from fastapi import APIRouter, File, HTTPException, UploadFile

from app.extraction.requirement_extractor import (
    RequirementExtractionError,
    RequirementExtractor,
)
from app.ingestion.document_loader import load_document


router = APIRouter(
    prefix="/api/analysis",
    tags=["analysis"],
)


@router.post("/extract-requirements")
async def extract_requirements(
    file: UploadFile = File(...),
):
    """
    Extract structured requirements from an uploaded RFP PDF.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A file is required.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty.",
        )

    import tempfile
    from pathlib import Path

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_file:
            temporary_file.write(contents)
            temporary_path = Path(
                temporary_file.name
            )

        document = load_document(
            temporary_path
        )

        extractor = RequirementExtractor()

        result = extractor.extract(
            document["text"]
        )

        return {
            "filename": file.filename,
            "file_type": document["file_type"],
            "page_count": document["page_count"],
            "character_count": document["character_count"],
            "requirements": [
                requirement.model_dump()
                for requirement in result.requirements
            ],
            "total_requirements": result.total_requirements,
        }

    except RequirementExtractionError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Requirement extraction failed: {exc}",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to process RFP: {exc}",
        ) from exc

    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
