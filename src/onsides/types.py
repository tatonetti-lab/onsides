from pydantic import BaseModel


class IndexedText(BaseModel):
    text_id: str
    text: str
