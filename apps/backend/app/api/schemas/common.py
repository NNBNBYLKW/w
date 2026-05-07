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


class RuntimeDiagnosticsResponse(BaseModel):
    process_id: int
    process_start_time: float
    sys_executable: str
    cwd: str
    data_dir: str
    database_path: str
    database_url: str
    pypdfium2_import: str
    pypdfium2_version: str | None
    pypdfium2_error: str | None
    packaged_backend: bool
