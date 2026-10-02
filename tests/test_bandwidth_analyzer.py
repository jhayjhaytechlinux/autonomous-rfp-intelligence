import json
from pathlib import Path

import pytest

from app.resources.bandwidth_analyzer import (
    BandwidthAnalyzer,
)
from app.resources.bandwidth_loader import (
    BandwidthDatasetLoadError,
    load_bandwidth_dataset,
)
from app.resources.schemas import (
    TeamBandwidthDataset,
)


DATASET_PATH = Path(
    "data/schedules/team_bandwidth.json"
)


def test_bandwidth_dataset_loads():
    """Test that the controlled bandwidth dataset loads correctly."""

    dataset = load_bandwidth_dataset(DATASET_PATH)

    assert isinstance(
        dataset,
        TeamBandwidthDataset,
    )

    assert dataset.company_name == "SecureOps Africa"
    assert dataset.dataset_type == "synthetic_demonstration"
    assert dataset.planning_period == "2026-Q4"
    assert len(dataset.teams) == 3


def test_bandwidth_totals_are_calculated():
    """Test aggregate team capacity calculations."""

    dataset = load_bandwidth_dataset(DATASET_PATH)

    assert dataset.total_available_hours == 1320
    assert dataset.total_allocated_hours == 870
    assert dataset.total_remaining_hours == 450


def test_bandwidth_analyzer_calculates_resource_score():
    """Test resource availability scoring."""

    dataset = load_bandwidth_dataset(DATASET_PATH)

    analyzer = BandwidthAnalyzer()

    result = analyzer.analyze(dataset)

    assert result.total_available_hours == 1320
    assert result.total_allocated_hours == 870
    assert result.total_remaining_hours == 450

    assert result.utilization_percentage == pytest.approx(
        65.91,
        abs=0.01,
    )

    assert result.resource_score == pytest.approx(
        34.09,
        abs=0.01,
    )


def test_bandwidth_analyzer_handles_zero_capacity():
    """Test behavior when no team capacity exists."""

    dataset = TeamBandwidthDataset(
        dataset_name="Zero Capacity Dataset",
        dataset_type="synthetic_test",
        description="Test dataset with no available capacity.",
        company_name="SecureOps Africa",
        planning_period="2026-Q4",
        teams=[],
    )

    analyzer = BandwidthAnalyzer()

    result = analyzer.analyze(dataset)

    assert result.total_available_hours == 0
    assert result.total_remaining_hours == 0
    assert result.resource_score == 0
    assert result.utilization_percentage == 100


def test_bandwidth_loader_rejects_missing_file(tmp_path):
    """Test that a missing bandwidth dataset is rejected."""

    missing_path = (
        tmp_path / "missing_bandwidth.json"
    )

    with pytest.raises(BandwidthDatasetLoadError):
        load_bandwidth_dataset(missing_path)


def test_bandwidth_loader_rejects_invalid_json(tmp_path):
    """Test that malformed JSON is rejected."""

    invalid_path = (
        tmp_path / "invalid_bandwidth.json"
    )

    invalid_path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    with pytest.raises(BandwidthDatasetLoadError):
        load_bandwidth_dataset(invalid_path)


def test_bandwidth_loader_rejects_invalid_structure(tmp_path):
    """Test that structurally invalid JSON is rejected."""

    invalid_path = (
        tmp_path / "invalid_structure.json"
    )

    invalid_path.write_text(
        json.dumps(
            {
                "dataset_name": "Invalid Dataset"
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BandwidthDatasetLoadError):
        load_bandwidth_dataset(invalid_path)
