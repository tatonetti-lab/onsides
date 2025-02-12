import asyncio
import logging
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer
from rich.logging import RichHandler

import onsides.download
from onsides.db import DrugLabelSource, SQLModel
from onsides.state import DEFAULT_DIRECTORY, State

app = typer.Typer(add_completion=False)
logger = logging.getLogger(__name__)
state = State()


def version_callback(value: bool):
    if value:
        typer.echo(f"OnSIDES version {version('onsides')}")
        raise typer.Exit()


@app.callback()
def main(
    directory: Annotated[
        Path, typer.Option(help="Path to the output SQLite database")
    ] = DEFAULT_DIRECTORY,
    force: Annotated[
        bool, typer.Option("--force", help="Force overwriting past work")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Show verbose output")
    ] = False,
    _: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            help="Show the version and exit",
            is_eager=True,
        ),
    ] = False,
):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )
    state.directory = directory
    state.force = force
    state.sqlite_path = directory.joinpath("working.db").as_posix()
    SQLModel.metadata.create_all(state.get_engine())


@app.command("download")
def download_labels(
    sources: Annotated[
        list[DrugLabelSource],
        typer.Argument(help="Which sources to download", show_default=False),
    ],
):
    logger.info(f"Will download the following sources: {[s.value for s in sources]}")

    async def download_simultaneously():
        coros = list()
        if DrugLabelSource.EU in sources:
            coros.append(onsides.download.download_eu(state))
        if DrugLabelSource.UK in sources:
            coros.append(onsides.download.download_uk(state))
        return await asyncio.gather(*coros)

    return asyncio.run(download_simultaneously())
