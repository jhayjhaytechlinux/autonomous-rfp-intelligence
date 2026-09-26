from pathlib import Path
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.analysis.rfp_analyzer import RFPAnalysisError, RFPAnalyzer
from app.compliance.capability_loader import (
    CapabilityProfileLoadError,
    load_capability_profile,
)
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

    Pipeline:

        PDF upload
            ↓
        Document ingestion
            ↓
        AI requirement extraction
    """

    # ---------------------------------------------------------
    # Validate uploaded file
    # ---------------------------------------------------------

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

    temporary_path: Path | None = None

    try:
        # -----------------------------------------------------
        # Create temporary PDF
        # -----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary_file:
            temporary_file.write(contents)
            temporary_path = Path(
                temporary_file.name
            )

        # -----------------------------------------------------
        # Load document
        # -----------------------------------------------------

        document = load_document(
            temporary_path
        )

        # -----------------------------------------------------
        # Extract requirements
        # -----------------------------------------------------

        extractor = RequirementExtractor()

        result = extractor.extract(
            document["text"]
        )

        # -----------------------------------------------------
        # Return structured response
        # -----------------------------------------------------

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
        # -----------------------------------------------------
        # Remove temporary file
        # -----------------------------------------------------

        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()


@router.post("/analyze")
async def analyze_rfp(
    rfp_file: UploadFile = File(...),
    capability_file: UploadFile = File(...),
    resource_score: float = Form(50),
):
    """
    Run the complete RFP intelligence pipeline.

    Pipeline:

        RFP PDF
            ↓
        Document ingestion
            ↓
        AI requirement extraction
            ↓
        Company capability profile
            ↓
        Compliance assessment
            ↓
        Bid/No-Bid decision
            ↓
        Complete JSON analysis

    This endpoint is the primary integration point
    for the n8n automation workflow.
    """

    # ---------------------------------------------------------
    # Validate RFP
    # ---------------------------------------------------------

    if not rfp_file.filename:
        raise HTTPException(
            status_code=400,
            detail="An RFP PDF file is required.",
        )

    if not rfp_file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="The RFP file must be a PDF.",
        )

    # ---------------------------------------------------------
    # Validate capability profile
    # ---------------------------------------------------------

    if not capability_file.filename:
        raise HTTPException(
            status_code=400,
            detail="A capability profile file is required.",
        )

    if not capability_file.filename.lower().endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="The capability profile must be a JSON file.",
        )

    # ---------------------------------------------------------
    # Validate resource score
    # ---------------------------------------------------------

    if resource_score < 0 or resource_score > 100:
        raise HTTPException(
            status_code=400,
            detail="resource_score must be between 0 and 100.",
        )

    # ---------------------------------------------------------
    # Read uploaded files
    # ---------------------------------------------------------

    rfp_contents = await rfp_file.read()

    if not rfp_contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded RFP PDF is empty.",
        )

    capability_contents = await capability_file.read()

    if not capability_contents:
        raise HTTPException(
            status_code=400,
            detail="The capability profile is empty.",
        )

    rfp_path: Path | None = None
    capability_path: Path | None = None

    try:
        # -----------------------------------------------------
        # Create temporary RFP file
        # -----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as rfp_temp_file:
            rfp_temp_file.write(
                rfp_contents
            )

            rfp_path = Path(
                rfp_temp_file.name
            )

        # -----------------------------------------------------
        # Create temporary capability profile
        # -----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            suffix=".json",
            delete=False
        ) as capability_temp_file:
            capability_temp_file.write(
                capability_contents
            )

            capability_path = Path(
                capability_temp_file.name
            )

        # -----------------------------------------------------
        # Validate capability profile
        # -----------------------------------------------------

        load_capability_profile(
            capability_path
        )

        # -----------------------------------------------------
        # Run complete RFP analysis
        # -----------------------------------------------------

        analyzer = RFPAnalyzer()

        result = analyzer.analyze(
            rfp_path=rfp_path,
            capability_path=capability_path,
            resource_score=resource_score,
        )

        # -----------------------------------------------------
        # Restore original uploaded filename
        #
        # The analyzer sees the temporary file path internally.
        # The API should expose the user's original filename.
        # -----------------------------------------------------

        result["rfp"]["filename"] = (
            rfp_file.filename
        )

        # -----------------------------------------------------
        # Return complete analysis
        # -----------------------------------------------------

        return {
            "status": "success",
            "message": (
                "RFP analysis completed successfully."
            ),
            "rfp_filename": rfp_file.filename,
            "capability_filename": (
                capability_file.filename
            ),
            "resource_score": resource_score,
            "analysis": result,
        }

    except CapabilityProfileLoadError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid capability profile: {exc}"
            ),
        ) from exc

    except RFPAnalysisError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                f"RFP analysis failed: {exc}"
            ),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to analyze RFP: {exc}"
            ),
        ) from exc

    finally:
        # -----------------------------------------------------
        # Remove temporary RFP file
        # -----------------------------------------------------

        if (
            rfp_path is not None
            and rfp_path.exists()
        ):
            rfp_path.unlink()

        # -----------------------------------------------------
        # Remove temporary capability profile
        # -----------------------------------------------------

        if (
            capability_path is not None
            and capability_path.exists()
        ):
            capability_path.unlink()
