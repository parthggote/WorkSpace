from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "#2563eb"
    icon: str = "sparkles"


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class WorkspaceOut(BaseModel):
    id: str
    name: str
    color: str | None = None
    icon: str | None = None


class ChatCreate(BaseModel):
    title: str | None = None


class ChatUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ChatOut(BaseModel):
    id: str
    workspace_id: str
    title: str | None = None


class ChatStreamRequest(BaseModel):
    workspace_id: str
    chat_id: str
    message: str = Field(min_length=1, max_length=8000)
    force_web: bool = False
    skip_web_prompt: bool = False
    advanced_search: bool = False
    document_ids: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    source: str
    title: str
    locator: str | None = None
    url: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    score: float | None = None
    excerpt: str | None = None
