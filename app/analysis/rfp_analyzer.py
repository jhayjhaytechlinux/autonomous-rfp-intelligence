import inspect
from pathlib import Path

from app.compliance.capability_loader import load_capability_profile
from app.compliance.compliance_engine import ComplianceEngine
from app.decision.decision_engine import DecisionEngine
from app.extraction.requirement_extractor import RequirementExtractor
from app.ingestion.document_loader import load_document
from app.pricing.pricing_analyzer import PricingAnalyzer
from app.pricing.pricing_loader import load_pricing_dataset
from app.proposals.proposal_loader import load_proposal_dataset
from app.proposals.relevance_analyzer import ProposalRelevanceAnalyzer
from app.resources.bandwidth_analyzer import BandwidthAnalyzer
from app.resources.bandwidth_loader import load_bandwidth_dataset
from app.scoring.win_probability import WinProbabilityAnalyzer


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
        Historical proposal relevance
            ↓
        Team bandwidth analysis
            ↓
        Pricing / commercial fit analysis
            ↓
        Win-probability scoring
            ↓
        Bid/No-Bid decision
    """

    DEFAULT_PROPOSAL_DATASET = (
        "data/past_proposals/winning_proposals.json"
    )

    DEFAULT_BANDWIDTH_DATASET = (
        "data/schedules/team_bandwidth.json"
    )

    DEFAULT_PRICING_DATASET = (
        "data/pricing/secureops_pricing.json"
    )

    def __init__(
        self,
        requirement_extractor: RequirementExtractor | None = None,
        compliance_engine: ComplianceEngine | None = None,
        decision_engine: DecisionEngine | None = None,
        proposal_relevance_analyzer: ProposalRelevanceAnalyzer | None = None,
        bandwidth_analyzer: BandwidthAnalyzer | None = None,
        pricing_analyzer: PricingAnalyzer | None = None,
        win_probability_analyzer: WinProbabilityAnalyzer | None = None,
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

        self.proposal_relevance_analyzer = (
            proposal_relevance_analyzer
            if proposal_relevance_analyzer is not None
            else ProposalRelevanceAnalyzer()
        )

        self.bandwidth_analyzer = (
            bandwidth_analyzer
            if bandwidth_analyzer is not None
            else BandwidthAnalyzer()
        )

        self.pricing_analyzer = (
            pricing_analyzer
            if pricing_analyzer is not None
            else PricingAnalyzer()
        )

        self.win_probability_analyzer = (
            win_probability_analyzer
            if win_probability_analyzer is not None
            else WinProbabilityAnalyzer()
        )

    def analyze(
        self,
        rfp_path: str | Path,
        capability_path: str | Path,
        resource_score: float | None = None,
        proposal_dataset_path: str | Path | None = None,
        bandwidth_dataset_path: str | Path | None = None,
        pricing_dataset_path: str | Path | None = None,
        project_value: float | None = None,
        service_category: str | None = None,
    ) -> dict:
        """
        Run the complete RFP intelligence pipeline.

        Args:
            rfp_path:
                Path to the RFP PDF.

            capability_path:
                Path to the company capability profile JSON.

            resource_score:
                Optional manual resource availability score from 0
                to 100.

                When omitted, the score is automatically calculated
                from the configured team bandwidth dataset.

                This parameter is retained for backward compatibility
                and controlled testing.

            proposal_dataset_path:
                Optional path to the historical winning-proposal
                dataset. When omitted, the controlled project
                demonstration dataset is used.

            bandwidth_dataset_path:
                Optional path to the team bandwidth dataset. When
                omitted, the controlled project demonstration dataset
                is used.

            pricing_dataset_path:
                Optional path to the company pricing dataset. When
                omitted, the controlled project demonstration dataset
                is used.

            project_value:
                Optional estimated commercial value of the RFP
                opportunity.

                When supplied, the pricing engine evaluates the
                opportunity against the available pricing models.

                When omitted, pricing coverage is reported without
                calculating a project-specific commercial-fit score.

            service_category:
                Optional service category used to prioritize a
                specific pricing model.

        Returns:
            Dictionary containing the complete structured analysis.

        Raises:
            RFPAnalysisError:
                If any stage of the pipeline fails.
        """

        rfp_path = Path(rfp_path)
        capability_path = Path(capability_path)

        if proposal_dataset_path is None:
            proposal_dataset_path = Path(
                self.DEFAULT_PROPOSAL_DATASET
            )
        else:
            proposal_dataset_path = Path(
                proposal_dataset_path
            )

        if bandwidth_dataset_path is None:
            bandwidth_dataset_path = Path(
                self.DEFAULT_BANDWIDTH_DATASET
            )
        else:
            bandwidth_dataset_path = Path(
                bandwidth_dataset_path
            )

        if pricing_dataset_path is None:
            pricing_dataset_path = Path(
                self.DEFAULT_PRICING_DATASET
            )
        else:
            pricing_dataset_path = Path(
                pricing_dataset_path
            )

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
            extraction = self.requirement_extractor.extract(
                rfp_text
            )

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
            # Stage 5: Load previous successful proposals
            # ---------------------------------------------------------
            proposal_dataset = load_proposal_dataset(
                proposal_dataset_path
            )

            # ---------------------------------------------------------
            # Stage 6: Calculate historical proposal relevance
            # ---------------------------------------------------------
            proposal_relevance = (
                self.proposal_relevance_analyzer.analyze(
                    compliance_matrix,
                    proposal_dataset.proposals,
                )
            )

            # ---------------------------------------------------------
            # Stage 7: Load and analyze team bandwidth
            # ---------------------------------------------------------
            bandwidth_dataset = load_bandwidth_dataset(
                bandwidth_dataset_path
            )

            bandwidth_analysis = self.bandwidth_analyzer.analyze(
                bandwidth_dataset
            )

            # ---------------------------------------------------------
            # Stage 8: Determine resource score
            # ---------------------------------------------------------
            calculated_resource_score = (
                bandwidth_analysis.resource_score
            )

            effective_resource_score = (
                calculated_resource_score
                if resource_score is None
                else resource_score
            )

            # ---------------------------------------------------------
            # Stage 9: Load and analyze pricing
            # ---------------------------------------------------------
            pricing_dataset = load_pricing_dataset(
                pricing_dataset_path
            )

            pricing_analysis = self.pricing_analyzer.analyze(
                pricing_dataset=pricing_dataset,
                project_value=project_value,
                service_category=service_category,
            )

            # ---------------------------------------------------------
            # Stage 10: Calculate evidence-based win probability
            # ---------------------------------------------------------
            win_probability = (
                self.win_probability_analyzer.analyze(
                    compliance_matrix=compliance_matrix,
                    requirements=extraction.requirements,
                    historical_relevance_score=(
                        proposal_relevance.relevance_score
                    ),
                )
            )

            # ---------------------------------------------------------
            # Stage 11: Calculate Bid/No-Bid decision
            # ---------------------------------------------------------
            #
            # The production DecisionEngine supports the
            # win_probability_score parameter.
            #
            # The compatibility check below preserves support for
            # injected/custom decision engines that still implement
            # the previous evaluate() signature.
            #
            decision_parameters = inspect.signature(
                self.decision_engine.evaluate
            ).parameters

            decision_kwargs = {
                "resource_score": effective_resource_score,
                "historical_relevance_score": (
                    proposal_relevance.relevance_score
                ),
                "matched_historical_proposals": (
                    proposal_relevance.matched_proposal_ids
                ),
            }

            if (
                "win_probability_score"
                in decision_parameters
                or any(
                    parameter.kind
                    == inspect.Parameter.VAR_KEYWORD
                    for parameter in decision_parameters.values()
                )
            ):
                decision_kwargs["win_probability_score"] = (
                    win_probability.score
                )

            decision = self.decision_engine.evaluate(
                compliance_matrix,
                extraction.requirements,
                **decision_kwargs,
            )

            # ---------------------------------------------------------
            # Stage 12: Return complete structured analysis
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
                "historical_proposals": {
                    "dataset_name": proposal_dataset.dataset_name,
                    "dataset_type": proposal_dataset.dataset_type,
                    "total_proposals": len(
                        proposal_dataset.proposals
                    ),
                    "matched_proposal_ids": (
                        proposal_relevance.matched_proposal_ids
                    ),
                    "matched_capability_ids": (
                        proposal_relevance.matched_capability_ids
                    ),
                    "relevance_score": (
                        proposal_relevance.relevance_score
                    ),
                },
                "bandwidth": {
                    "dataset_name": bandwidth_dataset.dataset_name,
                    "dataset_type": bandwidth_dataset.dataset_type,
                    "planning_period": (
                        bandwidth_dataset.planning_period
                    ),
                    "team_count": len(
                        bandwidth_dataset.teams
                    ),
                    "total_available_hours": (
                        bandwidth_analysis.total_available_hours
                    ),
                    "total_allocated_hours": (
                        bandwidth_analysis.total_allocated_hours
                    ),
                    "total_remaining_hours": (
                        bandwidth_analysis.total_remaining_hours
                    ),
                    "utilization_percentage": (
                        bandwidth_analysis.utilization_percentage
                    ),
                    "calculated_resource_score": (
                        bandwidth_analysis.resource_score
                    ),
                    "effective_resource_score": (
                        effective_resource_score
                    ),
                    "resource_score_source": (
                        "bandwidth_dataset"
                        if resource_score is None
                        else "manual_override"
                    ),
                },
                "pricing": {
                    "dataset_name": pricing_dataset.dataset_name,
                    "dataset_type": pricing_dataset.dataset_type,
                    "company_name": pricing_dataset.company_name,
                    "currency": pricing_dataset.currency,
                    "project_value": (
                        pricing_analysis.project_value
                    ),
                    "service_category": (
                        pricing_analysis.service_category
                    ),
                    "matched_model_id": (
                        pricing_analysis.matched_model_id
                    ),
                    "matched_model_name": (
                        pricing_analysis.matched_model_name
                    ),
                    "estimated_first_year_cost": (
                        pricing_analysis.estimated_first_year_cost
                    ),
                    "commercial_fit_score": (
                        pricing_analysis.commercial_fit_score
                    ),
                    "within_project_value_range": (
                        pricing_analysis.within_project_value_range
                    ),
                    "pricing_models_considered": (
                        pricing_analysis.pricing_models_considered
                    ),
                    "rationale": pricing_analysis.rationale,
                },
                "win_probability": {
                    "score": win_probability.score,
                    "compliance_component": (
                        win_probability.compliance_component
                    ),
                    "capability_component": (
                        win_probability.capability_component
                    ),
                    "experience_component": (
                        win_probability.experience_component
                    ),
                    "historical_component": (
                        win_probability.historical_component
                    ),
                    "interpretation": (
                        "Evidence-based decision-support score "
                        "from 0 to 100. This is not a statistically "
                        "calibrated probability."
                    ),
                },
                "decision": decision.model_dump(),
            }

        except RFPAnalysisError:
            raise

        except Exception as exc:
            raise RFPAnalysisError(
                f"RFP analysis failed: {exc}"
            ) from exc
