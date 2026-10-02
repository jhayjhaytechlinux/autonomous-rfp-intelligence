from pathlib import Path
import json

from pydantic import ValidationError

from app.resources.schemas import TeamBandwidthDataset


class BandwidthDatasetLoadError(Exception):
    """Raised when a team bandwidth dataset cannot be loaded."""


def load_bandwidth_dataset(
    file_path: str | Path,
) -> TeamBandwidthDataset:
    """
    Load and validate a team bandwidth dataset from JSON.
    """

    path = Path(file_path)

    if not path.exists():
        raise BandwidthDatasetLoadError(
            f"Team bandwidth dataset not found: {path}"
        )

    if path.suffix.lower() != ".json":
        raise BandwidthDatasetLoadError(
            f"Expected a JSON file, got: {path.suffix}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except json.JSONDecodeError as exc:
        raise BandwidthDatasetLoadError(
            f"Invalid JSON in bandwidth dataset: {exc}"
        ) from exc

    except OSError as exc:
        raise BandwidthDatasetLoadError(
            f"Unable to read bandwidth dataset: {exc}"
        ) from exc

    try:
        return TeamBandwidthDataset.model_validate(data)

    except ValidationError as exc:
        raise BandwidthDatasetLoadError(
            f"Invalid bandwidth dataset structure: {exc}"
        ) from exc
