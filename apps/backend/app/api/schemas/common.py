from pydantic import BaseModel


class ErrorInfo(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorInfo


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class SystemStatusResponse(BaseModel):
    app: str
    database: str
    sources_count: int
    tasks_count: int
    files_count: int
