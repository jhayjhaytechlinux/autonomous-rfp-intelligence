from pathlib import Path
import json

from pydantic import ValidationError

from app.compliance.schemas import CapabilityProfile


class CapabilityProfileLoadError(Exception):
    """Raised when a company capability profile cannot be loaded."""


def load_capability_profile(
    file_path: str | Path,
) -> CapabilityProfile:
    """
    Load and validate a company capability profile from a JSON file.
    """

    path = Path(file_path)

    if not path.exists():
        raise CapabilityProfileLoadError(
            f"Capability profile not found: {path}"
        )

    if path.suffix.lower() != ".json":
        raise CapabilityProfileLoadError(
            f"Expected a JSON file, got: {path.suffix}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise CapabilityProfileLoadError(
            f"Invalid JSON in capability profile: {exc}"
        ) from exc
    except OSError as exc:
        raise CapabilityProfileLoadError(
            f"Unable to read capability profile: {exc}"
        ) from exc

    try:
        return CapabilityProfile.model_validate(data)
    except ValidationError as exc:
        raise CapabilityProfileLoadError(
            f"Invalid capability profile structure: {exc}"
        ) from exc
