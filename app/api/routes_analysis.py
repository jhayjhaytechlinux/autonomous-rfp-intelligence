from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.analysis.rfp_analyzer import RFPAnalyzer
from app.compliance.capability_loader import load_capability_profile
from app.extraction.requirement_extractor import RequirementExtractor
from app.ingestion.document_loader import load_document


router = APIRouter(
    prefix="/api/analysis",
    tags=["Analysis"],
)


@router.post("/extract-requirements")
async def extract_requirements(
    file: UploadFile = File(...),
):
    """
    Extract structured requirements from an uploaded RFP PDF.

    The multipart upload field is named `file`.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="RFP filename is required.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty.",
        )

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / file.filename
        temp_path.write_bytes(file_bytes)

        try:
            document = load_document(temp_path)

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Document loading failed: {exc}",
            ) from exc

        try:
            extractor = RequirementExtractor()
            result = extractor.extract(document["text"])

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Requirement extraction failed: {exc}",
            ) from exc

    if hasattr(result, "model_dump"):
        extraction = result.model_dump()

        requirements = extraction.get(
            "requirements",
            [],
        )

        total_requirements = extraction.get(
            "total_requirements",
            len(requirements),
        )

    else:
        requirements = []

        for requirement in getattr(
            result,
            "requirements",
            [],
        ):
            if hasattr(requirement, "model_dump"):
                requirements.append(
                    requirement.model_dump()
                )
            else:
                requirements.append(requirement)

        total_requirements = getattr(
            result,
            "total_requirements",
            len(requirements),
        )

    return {
        "filename": document["filename"],
        "file_type": document["file_type"],
        "page_count": document["page_count"],
        "character_count": document["character_count"],
        "total_requirements": total_requirements,
        "requirements": requirements,
    }


@router.post("/analyze")
async def analyze_rfp(
    rfp_file: UploadFile = File(...),
    capability_file: UploadFile = File(...),
    resource_score: float = Form(50),
    project_value: float | None = Form(None),
    service_category: str | None = Form(None),
):
    """
    Run the complete RFP intelligence pipeline.

    Inputs:
    - RFP PDF
    - Company capability profile
    - Optional resource score
    - Optional project value
    - Optional service category

    The analysis pipeline combines:
    - RFP document ingestion
    - Requirement extraction
    - Capability matching
    - Compliance analysis
    - Historical proposal relevance
    - Team bandwidth analysis
    - Win-probability scoring
    - Pricing/commercial analysis
    - Bid/No-Bid decision support

    This endpoint is the primary integration point for
    orchestration tools such as n8n.
    """

    if not rfp_file.filename:
        raise HTTPException(
            status_code=400,
            detail="RFP filename is required.",
        )

    if not capability_file.filename:
        raise HTTPException(
            status_code=400,
            detail="Capability profile filename is required.",
        )

    if not rfp_file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="The RFP file must be a PDF.",
        )

    if not capability_file.filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="The capability profile must be a JSON file.",
        )

    if not 0 <= resource_score <= 100:
        raise HTTPException(
            status_code=400,
            detail="resource_score must be between 0 and 100.",
        )

    if project_value is not None and project_value < 0:
        raise HTTPException(
            status_code=400,
            detail="project_value cannot be negative.",
        )

    if service_category is not None:
        service_category = service_category.strip()

        if not service_category:
            service_category = None

    rfp_bytes = await rfp_file.read()
    capability_bytes = await capability_file.read()

    if not rfp_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded RFP PDF is empty.",
        )

    if not capability_bytes:
        raise HTTPException(
            status_code=400,
            detail="The capability profile is empty.",
        )

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        rfp_path = temp_path / rfp_file.filename
        capability_path = temp_path / capability_file.filename

        rfp_path.write_bytes(rfp_bytes)
        capability_path.write_bytes(capability_bytes)

        try:
            load_capability_profile(capability_path)

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid capability profile: {exc}",
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to validate capability profile: {exc}",
            ) from exc

        analyzer = RFPAnalyzer()

        analysis_kwargs = {
            "rfp_path": rfp_path,
            "capability_path": capability_path,
            "resource_score": resource_score,
        }

        if project_value is not None:
            analysis_kwargs["project_value"] = project_value

        if service_category is not None:
            analysis_kwargs["service_category"] = service_category

        try:
            result = analyzer.analyze(**analysis_kwargs)

        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"RFP analysis failed: {exc}",
            ) from exc

    return {
        "status": "success",
        "message": "RFP analysis completed successfully.",
        "rfp_filename": rfp_file.filename,
        "capability_filename": capability_file.filename,
        "resource_score": resource_score,
        "project_value": project_value,
        "service_category": service_category,
        "analysis": result,
    }
