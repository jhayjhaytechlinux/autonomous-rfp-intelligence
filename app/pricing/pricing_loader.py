import json
from pathlib import Path

from app.pricing.schemas import PricingDataset


def load_pricing_dataset(file_path: str | Path) -> PricingDataset:
    """
    Load and validate a pricing dataset from a JSON file.

    Args:
        file_path: Path to the pricing dataset JSON file.

    Returns:
        A validated PricingDataset instance.

    Raises:
        FileNotFoundError: If the pricing file does not exist.
        ValueError: If the file is not valid JSON or does not match
            the expected pricing dataset structure.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Pricing dataset not found: {path}")

    if not path.is_file():
        raise ValueError(f"Pricing dataset path is not a file: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError(
            f"Expected a JSON pricing dataset, got: {path.suffix}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in pricing dataset: {path}"
        ) from exc

    try:
        return PricingDataset.model_validate(data)
    except Exception as exc:
        raise ValueError(
            f"Invalid pricing dataset structure: {path}"
        ) from exc
