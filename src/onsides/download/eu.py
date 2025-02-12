import asyncio
import logging
import re
from enum import Enum
from pathlib import Path
from typing import Literal

import aiofiles
import httpx
import pandas as pd
import polars as pl
from aiolimiter import AsyncLimiter
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from pydantic import BaseModel, Field
from rich.progress import track
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import select

from onsides.db import DrugLabel, DrugLabelSource
from onsides.state import State

logger = logging.getLogger(__name__)

limiter = AsyncLimiter(8)

ROOT_URL = "https://www.ema.europa.eu"


async def download_eu(state: State) -> None:
    logger.debug("EU: Ensuring directory")
    eu_path = state.directory.joinpath("eu")
    eu_path.mkdir(exist_ok=True, parents=True)

    async with httpx.AsyncClient() as client:
        logger.debug("EU: Ensuring manifest table")
        manifest_path = eu_path.joinpath("manifest.xlsx")
        await download_manifest(client, manifest_path)

        logger.debug("EU: Gathering drugs from the manifest file")
        drugs = await read_manifest(manifest_path)

        logger.debug("EU: Downloading remaining drug labels")
        label_pdf_directory = eu_path.joinpath("pdf_labels")
        label_pdf_directory.mkdir(exist_ok=True)
        for drug in track(drugs, description="EU labels..."):
            await download_and_save(
                drug, client, state.get_async_session(), label_pdf_directory
            )
        logger.info("EU: Finished downloading")


async def download_manifest(client: httpx.AsyncClient, output_path: Path) -> None:
    """Download the excel spreadsheet that lists all EU drugs"""

    manifest_url = (
        f"{ROOT_URL}/en/documents/report/medicines-output-medicines-report_en.xlsx"
    )
    if output_path.exists():
        logger.info(f"Skip downloading EU manifest: {output_path}")
        return None

    async with limiter:
        response = await client.get(manifest_url)

    async with aiofiles.open(output_path, "wb") as f:
        await f.write(response.content)


class EmaDrugLabelBase(BaseModel):
    name: str = Field(validation_alias="Name of medicine")
    code: str = Field(validation_alias="EMA product number")
    page_url: str = Field(validation_alias="Medicine URL")


class EmaDrugLabelFile(BaseModel):
    name: str
    code: str
    page_url: str
    path: Path


class EmaDrugLabelText(EmaDrugLabelFile):
    raw_text: str


async def read_manifest(manifest_path: Path) -> list[EmaDrugLabelBase]:
    records = (
        pd.read_excel(manifest_path, skiprows=8)
        .pipe(pl.DataFrame)
        .filter(pl.col("Category").eq("Human"))
        .to_dicts()
    )
    return [EmaDrugLabelBase.model_validate(row) for row in records]


async def download_and_save(
    drug: EmaDrugLabelBase,
    client: httpx.AsyncClient,
    async_session: async_sessionmaker[AsyncSession],
    directory: Path,
) -> None:
    label_id = None
    existing = await get_db_label(drug.code, async_session)
    if existing is not None:
        if existing.pdf_path is not None and Path(existing.pdf_path).exists():
            return
        label_id = existing.label_id

    drug_file = assign_path(drug, directory)
    if not drug_file.path.exists():
        result = await download_label(drug_file, client)
        if isinstance(result, AcquireLabelError):
            logger.error(f"EU: Error fetching {result}")
            return

    full_label = await load_pdf(drug_file)
    await save_label_db(full_label, label_id, async_session)


class AcquireLabelError(Enum):
    RATE_LIMIT = 1
    OTHER_HTTP_ERROR = 2
    NO_PRODUCT_INFO_SECTION = 3


class DownloadError(Enum):
    RATE_LIMIT = 1
    OTHER_HTTP_ERROR = 2


async def download_label(
    drug: EmaDrugLabelFile, client: httpx.AsyncClient
) -> EmaDrugLabelFile | AcquireLabelError:
    url_suffix = await download_label_page(drug, client)
    if isinstance(url_suffix, AcquireLabelError):
        return url_suffix

    pdf_url = f"{ROOT_URL}{url_suffix}"
    pdf_response = await download_helper(pdf_url, client, "bytes")
    if isinstance(pdf_response, DownloadError):
        return AcquireLabelError(pdf_response.value)
    assert isinstance(pdf_response, bytes)

    async with aiofiles.open(drug.path, "wb") as f:
        await f.write(pdf_response)

    return drug


async def download_label_page(
    drug: EmaDrugLabelFile, client: httpx.AsyncClient
) -> str | AcquireLabelError:
    page = await download_helper(drug.page_url, client, "text")
    if isinstance(page, DownloadError):
        return AcquireLabelError(page.value)
    assert isinstance(page, str)
    soup = BeautifulSoup(page, "html.parser")
    section = soup.find("div", id="ema-inpage-item-product-info")
    if section is None or isinstance(section, NavigableString):
        logger.error(f"EU: Couldn't find the product info section: {drug.name}")
        return AcquireLabelError.NO_PRODUCT_INFO_SECTION

    assert isinstance(section, Tag)
    links = section.find_all("a", target="_blank", href=True)
    reg = r"^/en/documents/product-information/.+-epar-product-information_en.pdf$"
    for link in links:
        match = re.match(reg, link["href"])  # type: ignore
        if match is not None:
            return match.group(0)

    logger.error(f"EU: Couldn't find the product info url: {drug.name}")
    return AcquireLabelError.NO_PRODUCT_INFO_SECTION


async def download_helper(
    url: str, client: httpx.AsyncClient, kind: Literal["bytes", "text"]
) -> str | bytes | DownloadError:
    async with limiter:
        response = await client.get(url)
    try:
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning(f"EU: Error status: {response.status_code}")
        if response.status_code == 429:
            return DownloadError.RATE_LIMIT
        return DownloadError.OTHER_HTTP_ERROR

    match kind:
        case "bytes":
            return response.content
        case "text":
            return response.text


def assign_path(drug: EmaDrugLabelBase, directory: Path) -> EmaDrugLabelFile:
    values = drug.model_dump()
    name = drug.code.replace("/", "_")
    values["path"] = directory.joinpath(name).with_suffix(".pdf")
    return EmaDrugLabelFile.model_validate(values)


async def get_db_label(
    code: str, async_session: async_sessionmaker[AsyncSession]
) -> DrugLabel | None:
    async with async_session() as session:
        query = (
            select(DrugLabel)
            .where(DrugLabel.source == DrugLabelSource.EU)
            .where(DrugLabel.source_id == code)
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def save_label_db(
    label: EmaDrugLabelText,
    label_id: int | None,
    async_session: async_sessionmaker[AsyncSession],
) -> None:
    row = DrugLabel(
        label_id=label_id,
        source=DrugLabelSource.EU,
        source_id=label.code,
        source_name=label.name,
        label_url=label.page_url,
        pdf_path=label.path.resolve().as_posix(),
        raw_text=label.raw_text,
    )
    async with async_session() as session, session.begin():
        session.add(row)


async def load_pdf(label: EmaDrugLabelFile) -> EmaDrugLabelText:
    cmd = ["pdftotext", "-nopgbrk", "-raw", label.path.resolve().as_posix(), "-"]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        error_message = stderr.decode("utf-8").strip()
        raise RuntimeError(f"EU: pdftotext failed: {error_message}")

    raw_text = stdout.decode("utf-8")
    return EmaDrugLabelText(
        name=label.name,
        code=label.code,
        page_url=label.page_url,
        path=label.path,
        raw_text=raw_text,
    )
