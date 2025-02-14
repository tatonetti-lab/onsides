import enum

from sqlmodel import Field, SQLModel


class DrugLabelSource(str, enum.Enum):
    US = "US"
    UK = "UK"
    EU = "EU"
    JP = "JP"


class DrugLabel(SQLModel, table=True):
    __tablename__: str = "drug_label"  # type: ignore

    label_id: int | None = Field(default=None, primary_key=True)
    source: DrugLabelSource
    source_name: str
    source_id: str
    pdf_path: str | None = None
    label_url: str | None
    raw_text: str | None
