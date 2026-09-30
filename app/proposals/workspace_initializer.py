from datetime import datetime, timezone
import json
from pathlib import Path
import re

from app.decision.schemas import BidDecision


class ProposalWorkspaceError(Exception):
    """Raised when a proposal workspace cannot be created."""


class ProposalWorkspaceInitializer:
    """
    Creates a controlled proposal workspace for a positive RFP decision.

    Workspace creation is intentionally separate from RFP analysis so that
    repeated analysis runs do not create proposal workspaces as a side effect.

    Supported workflow:
        BID -> create workspace
        EXECUTIVE_REVIEW -> wait for approval
        NO_BID -> no workspace
    """

    DEFAULT_ROOT = Path("proposal_workspaces")

    WORKSPACE_DIRECTORIES = (
        "requirements",
        "compliance",
        "historical",
        "pricing",
        "resources",
        "proposal",
    )

    OPPORTUNITY_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$"
    )

    def __init__(self, root_path: str | Path | None = None):
        self.root_path = (
            Path(root_path)
            if root_path is not None
            else self.DEFAULT_ROOT
        )

    def _validate_opportunity_id(self, opportunity_id: str) -> str:
        """
        Validate and normalize the opportunity ID used as a directory name.

        Only simple identifier characters are allowed so that the opportunity
        ID cannot escape the configured workspace root through path traversal
        or absolute-path manipulation.
        """

        opportunity_id = opportunity_id.strip()

        if not opportunity_id:
            raise ProposalWorkspaceError(
                "opportunity_id must not be empty."
            )

        if not self.OPPORTUNITY_ID_PATTERN.fullmatch(opportunity_id):
            raise ProposalWorkspaceError(
                "opportunity_id must contain only letters, numbers, "
                "dots, underscores, and hyphens, and must be no more "
                "than 100 characters."
            )

        return opportunity_id

    def initialize(
        self,
        opportunity_id: str,
        decision: BidDecision | str,
        decision_score: float,
        win_probability_score: float = 0,
        matched_historical_proposals: list[str] | None = None,
        company_name: str = "SecureOps Africa",
    ) -> dict:
        """
        Create a proposal workspace for a BID decision.

        Raises:
            ProposalWorkspaceError:
                If the opportunity ID or scores are invalid, or if a
                workspace is requested for a non-BID decision.
        """

        opportunity_id = self._validate_opportunity_id(
            opportunity_id
        )

        if not 0 <= decision_score <= 100:
            raise ProposalWorkspaceError(
                "decision_score must be between 0 and 100."
            )

        if not 0 <= win_probability_score <= 100:
            raise ProposalWorkspaceError(
                "win_probability_score must be between 0 and 100."
            )

        try:
            normalized_decision = BidDecision(decision)
        except ValueError as exc:
            raise ProposalWorkspaceError(
                f"Unsupported decision: {decision}"
            ) from exc

        if normalized_decision != BidDecision.BID:
            raise ProposalWorkspaceError(
                "Proposal workspace creation requires a BID decision."
            )

        workspace_root = self.root_path.resolve()
        workspace_path = workspace_root / opportunity_id

        try:
            workspace_path = workspace_path.resolve()

            if (
                workspace_path.parent != workspace_root
                or workspace_path == workspace_root
            ):
                raise ProposalWorkspaceError(
                    "Invalid opportunity_id: workspace path escapes "
                    "the configured workspace root."
                )

            workspace_path.mkdir(
                parents=True,
                exist_ok=True,
            )

            for directory in self.WORKSPACE_DIRECTORIES:
                (workspace_path / directory).mkdir(
                    parents=True,
                    exist_ok=True,
                )

            created_at = datetime.now(timezone.utc).isoformat()

            metadata = {
                "opportunity_id": opportunity_id,
                "company_name": company_name,
                "decision": normalized_decision.value,
                "decision_score": round(decision_score, 2),
                "win_probability_score": round(
                    win_probability_score,
                    2,
                ),
                "matched_historical_proposals": (
                    matched_historical_proposals or []
                ),
                "workspace_status": "initialized",
                "created_at": created_at,
            }

            metadata_path = workspace_path / "decision.json"

            with metadata_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    metadata,
                    file,
                    indent=2,
                )
                file.write("\n")

            readme_path = workspace_path / "README.md"

            readme_content = (
                f"# Proposal Workspace — {opportunity_id}\n\n"
                f"**Company:** {company_name}\n\n"
                f"**Decision:** {normalized_decision.value}\n\n"
                f"**Decision Score:** "
                f"{metadata['decision_score']}/100\n\n"
                f"**Win-Probability Score:** "
                f"{metadata['win_probability_score']}/100\n\n"
                "## Workspace Purpose\n\n"
                "This workspace was automatically initialized "
                "after a positive bid decision.\n\n"
                "## Directories\n\n"
                "- `requirements/` — extracted RFP requirements\n"
                "- `compliance/` — compliance matrix and gap analysis\n"
                "- `historical/` — relevant previous proposals\n"
                "- `pricing/` — commercial and pricing analysis\n"
                "- `resources/` — resource and bandwidth analysis\n"
                "- `proposal/` — proposal development materials\n"
            )

            with readme_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                file.write(readme_content)

        except ProposalWorkspaceError:
            raise

        except OSError as exc:
            raise ProposalWorkspaceError(
                f"Unable to initialize proposal workspace: {exc}"
            ) from exc

        return {
            "workspace_id": opportunity_id,
            "workspace_path": str(workspace_path),
            "workspace_status": "initialized",
            "decision": normalized_decision.value,
            "decision_score": round(decision_score, 2),
            "win_probability_score": round(
                win_probability_score,
                2,
            ),
            "metadata_file": str(metadata_path),
            "readme_file": str(readme_path),
            "directories": list(self.WORKSPACE_DIRECTORIES),
        }
