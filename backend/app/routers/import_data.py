from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.imports import ImportUploadResponse
from app.services import import_excel_file

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/upload", response_model=ImportUploadResponse)
async def upload_excel(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=400, detail="Only .xlsx or .xlsm files are supported"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        return await import_excel_file(
            file_bytes=file_bytes,
            file_name=filename,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc
