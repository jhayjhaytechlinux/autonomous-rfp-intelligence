from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.ingestion.document_loader import load_document


router = APIRouter(
    prefix="/api/rfp",
    tags=["RFP"],
)


@router.post("/upload")
async def upload_rfp(file: UploadFile = File(...)):
    """
    Upload an RFP PDF and extract its contents.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    if Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported.",
        )

    temporary_path = None

    try:
        with NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            content = await file.read()
            temporary_file.write(content)

        document = load_document(temporary_path)

        return {
            "status": "success",
            "filename": file.filename,
            "file_type": document["file_type"],
            "page_count": document["page_count"],
            "character_count": document["character_count"],
            "text": document["text"],
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
