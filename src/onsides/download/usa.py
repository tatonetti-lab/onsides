import asyncio
import logging
from enum import Enum
from pathlib import Path
from zipfile import ZipFile

import aiofiles
import aiofiles.os
import httpx
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import select

from onsides.db import DrugLabel, DrugLabelSource
from onsides.state import State

logger = logging.getLogger(__name__)

limiter = AsyncLimiter(8)


class AcquireLabelError(Enum):
    RATE_LIMIT = 1
    OTHER_HTTP_ERROR = 2
    NO_PRODUCT_INFO_SECTION = 3


class DownloadError(Enum):
    RATE_LIMIT = 1
    OTHER_HTTP_ERROR = 2


async def download_us(state: State) -> None:
    logger.debug("US: Ensuring directory")
    us_path = state.directory.joinpath("us")
    us_path.mkdir(exist_ok=True, parents=True)

    logger.info("US: Getting a list of all files to download")
    async with httpx.AsyncClient() as client:
        urls = await gather_dailymed_file_urls(client)
        if isinstance(urls, DownloadError):
            raise ValueError("US: Bad download page, layout must have changed")

        logger.info(f"US: Found {len(urls)} files on DailyMed. Downloading...")
        zip_paths = await download_zip_files(client, urls, us_path)

    logger.info("US: Unzipping all DailyMed files")
    for file in zip_paths:
        await unzip(file)

    result_files = list(us_path.joinpath("prescription").glob("*"))
    logger.info(f"US: Got {len(result_files)} files after unzipping")
    task = state.add_task(
        "us-to-db", "US: Extracting XML files to DB", total=len(result_files)
    )
    for result_zip in result_files:
        await label_to_db(result_zip, state.get_async_session())
        state.progress.update(task, advance=1)

    logger.info("US: Finished saving all labels to the database")


async def gather_dailymed_file_urls(
    client: httpx.AsyncClient,
) -> list[str] | DownloadError:
    download_url = (
        "https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm"
    )
    download_page = await get_helper(download_url, client)
    if isinstance(download_page, DownloadError):
        return download_page

    results = list()
    soup = BeautifulSoup(download_page, "html.parser")
    parts = soup.find_all("li", {"data-ddfilter": "human prescription labels"})
    for part in parts:
        if not isinstance(part, Tag):
            continue
        links = part.find_all("a", href=True)
        for link in links:
            if link.text == "HTTPS":
                results.append(link["href"])  # type: ignore

    return results


async def download_file(
    client: httpx.AsyncClient, url: str, output_path: Path
) -> None | DownloadError:
    async with (
        client.stream("GET", url) as response,
        aiofiles.open(output_path, "wb") as file,
    ):
        try:
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning(f"US: Error downloading: {e}")
            if response.status_code == 429:
                return DownloadError.RATE_LIMIT
            return DownloadError.OTHER_HTTP_ERROR

        # Get total size if available
        total = int(response.headers.get("content-length", 0))
        current_decile = 0

        # Stream the download to the output file
        async for chunk in response.aiter_bytes(chunk_size=8192):
            await file.write(chunk)

            if total:
                downloaded = await file.tell()
                percent = int(100 * downloaded / total)
                if percent > current_decile + 10:
                    current_decile += 10
                    logger.info(f"US: downloading: {current_decile}%")
    return None


async def download_zip_files(
    client: httpx.AsyncClient, urls: list[str], output_dir: Path
) -> list[Path]:
    zip_paths = list()
    for i, url in enumerate(urls):
        file_name = Path(url).name
        output_path = output_dir.joinpath(file_name)
        zip_paths.append(output_path)
        if output_path.exists():
            logger.info(f"US: Skipping {file_name}, already downloaded")
        else:
            logger.info(f"US: Downloading file {i + 1}/{len(urls)}")
            result = await download_file(client, url, output_path)
            if isinstance(result, DownloadError):
                raise ValueError("US: Error downloading the file from DailyMed")
    return zip_paths


async def get_helper(url: str, client: httpx.AsyncClient) -> str | DownloadError:
    async with limiter:
        response = await client.get(url)
    try:
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning(f"US: Error status: {response.status_code}")
        if response.status_code == 429:
            return DownloadError.RATE_LIMIT
        return DownloadError.OTHER_HTTP_ERROR

    return response.text


async def unzip(zip_path: Path):
    try:
        extract_dir = zip_path.parent
        await asyncio.to_thread(ZipFile(zip_path).extractall, path=extract_dir)
    except Exception as e:
        raise ValueError(f"Error extracting {zip_path}") from e


class XmlFileContents(BaseModel):
    dailymed_id: str
    xml: str


async def extract_xml_from_zip(zip_path: Path) -> XmlFileContents | None:
    async with aiofiles.tempfile.TemporaryDirectory() as temp_dir:
        with ZipFile(zip_path, "r") as zip_parent:
            infolist = zip_parent.infolist()
            for file in infolist:
                if not file.filename.endswith(".xml"):
                    continue

                dailymed_id = Path(file.filename).stem
                output_path = zip_parent.extract(file, path=temp_dir)
                async with aiofiles.open(output_path) as xml_file:
                    contents = await xml_file.read()
                    return XmlFileContents(dailymed_id=dailymed_id, xml=contents)
    return None


async def label_to_db(
    drug_zip_path: Path, async_session: async_sessionmaker[AsyncSession]
) -> None:
    contents = await extract_xml_from_zip(drug_zip_path)
    if contents is None:
        logger.error(f"US: Unable to find an XML file in {drug_zip_path}")
        return

    async with async_session() as session:
        query = (
            select(DrugLabel)
            .where(DrugLabel.source == DrugLabelSource.US)
            .where(DrugLabel.source_id == contents.dailymed_id)
        )
        result = await session.execute(query)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return None

        soup = BeautifulSoup(contents.xml, features="xml")
        set_id = soup.find("setId")
        if set_id is None:
            raise ValueError(f"US: No set_id found in {drug_zip_path}")

        label = DrugLabel(
            source=DrugLabelSource.US,
            source_name=set_id.text.strip(),
            source_id=contents.dailymed_id,
            label_url=None,
            raw_text=contents.xml,
        )
        async with async_session() as session, session.begin():
            session.add(label)

    return None
