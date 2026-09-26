from pathlib import Path

from app.compliance.capability_loader import load_capability_profile
from app.compliance.compliance_engine import ComplianceEngine
from app.decision.decision_engine import DecisionEngine
from app.decision.schemas import DecisionResult
from app.extraction.requirement_extractor import RequirementExtractor
from app.ingestion.document_loader import load_document


class RFPAnalysisError(Exception):
    """Raised when the end-to-end RFP analysis fails."""


class RFPAnalyzer:
    """
    Orchestrates the complete RFP intelligence pipeline.

    Pipeline:

        RFP PDF
            ↓
        Document ingestion
            ↓
        AI requirement extraction
            ↓
        Company capability loading
            ↓
        Compliance assessment
            ↓
        Bid/No-Bid decision
    """

    def __init__(
        self,
        requirement_extractor: RequirementExtractor | None = None,
        compliance_engine: ComplianceEngine | None = None,
        decision_engine: DecisionEngine | None = None,
    ):
        self.requirement_extractor = (
            requirement_extractor
            if requirement_extractor is not None
            else RequirementExtractor()
        )

        self.compliance_engine = (
            compliance_engine
            if compliance_engine is not None
            else ComplianceEngine()
        )

        self.decision_engine = (
            decision_engine
            if decision_engine is not None
            else DecisionEngine()
        )

    def analyze(
        self,
        rfp_path: str | Path,
        capability_path: str | Path,
        resource_score: float = 50,
    ) -> dict:
        """
        Run the complete RFP analysis pipeline.

        Args:
            rfp_path:
                Path to the RFP PDF.

            capability_path:
                Path to the company capability profile JSON.

            resource_score:
                Current resource availability score from 0 to 100.
                This will later be calculated automatically from
                team bandwidth data.

        Returns:
            Dictionary containing the complete analysis.

        Raises:
            RFPAnalysisError:
                If any stage of the pipeline fails.
        """

        rfp_path = Path(rfp_path)
        capability_path = Path(capability_path)

        try:
            # ---------------------------------------------------------
            # Stage 1: Load and extract the RFP document
            # ---------------------------------------------------------
            document = load_document(rfp_path)

            rfp_text = document["text"]

            if not rfp_text.strip():
                raise RFPAnalysisError(
                    "The RFP document does not contain extractable text."
                )

            # ---------------------------------------------------------
            # Stage 2: Extract requirements using the configured LLM
            # ---------------------------------------------------------
            extraction = self.requirement_extractor.extract(rfp_text)

            # ---------------------------------------------------------
            # Stage 3: Load company capability profile
            # ---------------------------------------------------------
            capability_profile = load_capability_profile(
                capability_path
            )

            # ---------------------------------------------------------
            # Stage 4: Assess compliance
            # ---------------------------------------------------------
            compliance_matrix = self.compliance_engine.assess(
                extraction.requirements,
                capability_profile,
            )

            # ---------------------------------------------------------
            # Stage 5: Calculate Bid/No-Bid decision
            # ---------------------------------------------------------
            decision = self.decision_engine.evaluate(
                compliance_matrix,
                extraction.requirements,
                resource_score=resource_score,
            )

            # ---------------------------------------------------------
            # Stage 6: Return complete structured analysis
            # ---------------------------------------------------------
            return {
                "rfp": {
                    "filename": rfp_path.name,
                    "file_type": document["file_type"],
                    "page_count": document["page_count"],
                    "character_count": document["character_count"],
                },
                "company": {
                    "name": capability_profile.company_name,
                    "type": capability_profile.company_type,
                },
                "requirements": {
                    "total": extraction.total_requirements,
                    "items": [
                        requirement.model_dump()
                        for requirement in extraction.requirements
                    ],
                },
                "compliance": compliance_matrix.model_dump(),
                "decision": decision.model_dump(),
            }

        except RFPAnalysisError:
            raise

        except Exception as exc:
            raise RFPAnalysisError(
                f"RFP analysis failed: {exc}"
            ) from exc
