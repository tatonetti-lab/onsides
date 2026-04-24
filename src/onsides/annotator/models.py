from pydantic import BaseModel


class VocabSourceConfig(BaseModel):
    vocab_id: str
    path: str
    highlight_color: str = "#fff3cd"


class AnnotationField(BaseModel):
    name: str
    field_type: str
    options: list[str] | None = None
    required: bool = False


class AnnotationSchema(BaseModel):
    entity_type: str
    allow_free_text: bool = True
    fields: list[AnnotationField] = []


class TaskDefinition(BaseModel):
    task_id: str
    name: str
    description: str
    vocab_sources: list[VocabSourceConfig]
    sections: list[str]
    label_pool: list[str] | None = None
    annotation_schema: AnnotationSchema


class VocabMatch(BaseModel):
    term: str
    code: str
    start: int
    length: int
    pt_code: str | None = None
    pt_name: str | None = None
    vocab_id: str


class LabelSummary(BaseModel):
    set_id: str
    title: str
    drug_name: str = ""
    date: str
    sections_available: list[str]
    annotation_status: str = "not_started"


class LabelSection(BaseModel):
    section_code: str
    text: str
    vocab_matches: list[VocabMatch]


class LabelDetail(BaseModel):
    set_id: str
    title: str
    drug_name: str = ""
    sections: list[LabelSection]


class Annotation(BaseModel):
    id: str
    entity_type: str
    term_text: str
    term_code: str | None = None
    pt_code: str | None = None
    pt_name: str | None = None
    start: int
    end: int
    section_code: str
    source: str
    extra_fields: dict[str, str] = {}


class AnnotationDocument(BaseModel):
    task_id: str
    label_id: str
    label_title: str
    annotator: str
    status: str = "in_progress"
    created_at: str
    updated_at: str
    sections: dict[str, list[Annotation]]
    notes: str = ""


class AnnotationListItem(BaseModel):
    label_id: str
    label_title: str
    drug_name: str = ""
    status: str
    updated_at: str
    annotation_count: int


class VocabSearchResult(BaseModel):
    term: str
    code: str
    pt_code: str | None = None
    pt_name: str | None = None
    vocab_id: str
