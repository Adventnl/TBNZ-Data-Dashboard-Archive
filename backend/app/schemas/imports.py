from pydantic import BaseModel, Field


class ImportSheetResult(BaseModel):
    sheet_name: str
    dataset: str
    total_rows: int = 0
    valid_rows: int = 0
    imported_rows: int = 0
    duplicate_rows: int = 0
    skipped_rows: int = 0
    errors: list[str] = Field(default_factory=list)


class ImportUploadResponse(BaseModel):
    file_name: str
    status: str
    total_rows: int = 0
    imported_rows: int = 0
    duplicate_rows: int = 0
    error_rows: int = 0
    summary: list[ImportSheetResult] = Field(default_factory=list)
