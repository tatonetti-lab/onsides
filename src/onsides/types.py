from pydantic import BaseModel


class IndexedText(BaseModel):
    text_id: int
    text: str
