from pathlib import Path
import json

from pydantic import ValidationError

from app.proposals.schemas import PastProposalDataset


class ProposalDatasetLoadError(Exception):
    """Raised when a past proposal dataset cannot be loaded."""


def load_proposal_dataset(file_path: str | Path) -> PastProposalDataset:
    path = Path(file_path)

    if not path.exists():
        raise ProposalDatasetLoadError(
            f"Past proposal dataset not found: {path}"
        )

    if path.suffix.lower() != ".json":
        raise ProposalDatasetLoadError(
            f"Expected a JSON file, got: {path.suffix}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ProposalDatasetLoadError(
            f"Invalid JSON in proposal dataset: {exc}"
        ) from exc
    except OSError as exc:
        raise ProposalDatasetLoadError(
            f"Unable to read proposal dataset: {exc}"
        ) from exc

    try:
        return PastProposalDataset.model_validate(data)
    except ValidationError as exc:
        raise ProposalDatasetLoadError(
            f"Invalid proposal dataset structure: {exc}"
        ) from exc
