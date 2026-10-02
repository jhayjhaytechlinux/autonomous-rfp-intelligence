from pathlib import Path

import pytest

from app.pricing.pricing_analyzer import PricingAnalyzer
from app.pricing.pricing_loader import load_pricing_dataset


PRICING_DATASET_PATH = Path(
    "data/pricing/secureops_pricing.json"
)


@pytest.fixture
def pricing_dataset():
    return load_pricing_dataset(PRICING_DATASET_PATH)


@pytest.fixture
def analyzer():
    return PricingAnalyzer()


def test_load_pricing_dataset(pricing_dataset):
    assert pricing_dataset.company_name == "SecureOps Africa"
    assert pricing_dataset.currency == "USD"
    assert len(pricing_dataset.pricing_models) == 4


def test_first_year_cost_calculation(pricing_dataset):
    model = pricing_dataset.pricing_models[0]

    assert model.model_id == "PRICE-001"
    assert model.estimated_first_year_cost == 68000


def test_project_value_supported(pricing_dataset):
    model = pricing_dataset.pricing_models[0]

    assert model.supports_project_value(100000) is True
    assert model.supports_project_value(50000) is True
    assert model.supports_project_value(150000) is True


def test_project_value_outside_supported_range(pricing_dataset):
    model = pricing_dataset.pricing_models[0]

    assert model.supports_project_value(40000) is False
    assert model.supports_project_value(160000) is False


def test_security_monitoring_pricing_match(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=100000,
        service_category="security_monitoring",
    )

    assert result.matched_model_id == "PRICE-001"
    assert result.matched_model_name == (
        "Enterprise Security Monitoring"
    )
    assert result.service_category == "security_monitoring"
    assert result.project_value == 100000
    assert result.estimated_first_year_cost == 68000
    assert result.within_project_value_range is True
    assert result.pricing_models_considered == 1
    assert result.commercial_fit_score == 88.0


def test_siem_pricing_match(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=120000,
        service_category="siem",
    )

    assert result.matched_model_id == "PRICE-002"
    assert result.matched_model_name == (
        "Enterprise SIEM Implementation"
    )
    assert result.service_category == "siem"
    assert result.within_project_value_range is True


def test_network_security_pricing_match(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=80000,
        service_category="network_security",
    )

    assert result.matched_model_id == "PRICE-003"
    assert result.matched_model_name == (
        "Network Security Monitoring"
    )
    assert result.within_project_value_range is True


def test_consulting_training_pricing_match(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=50000,
        service_category="consulting_training",
    )

    assert result.matched_model_id == "PRICE-004"
    assert result.matched_model_name == (
        "Cybersecurity Consulting and Training"
    )
    assert result.within_project_value_range is True


def test_missing_project_value(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=None,
        service_category="security_monitoring",
    )

    assert result.matched_model_id is None
    assert result.project_value is None
    assert result.commercial_fit_score == 0
    assert result.pricing_models_considered == 1
    assert result.within_project_value_range is False


def test_unknown_service_category_falls_back_to_all_models(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=100000,
        service_category="unknown_service",
    )

    assert result.matched_model_id == "PRICE-003"
    assert result.matched_model_name == (
        "Network Security Monitoring"
    )
    assert result.pricing_models_considered == 4


def test_out_of_range_project_value(
    analyzer,
    pricing_dataset,
):
    result = analyzer.analyze(
        pricing_dataset=pricing_dataset,
        project_value=300000,
        service_category="security_monitoring",
    )

    assert result.matched_model_id == "PRICE-001"
    assert result.within_project_value_range is False
    assert result.commercial_fit_score < 80


def test_negative_project_value_rejected(
    analyzer,
    pricing_dataset,
):
    with pytest.raises(ValueError, match="cannot be negative"):
        analyzer.analyze(
            pricing_dataset=pricing_dataset,
            project_value=-1000,
            service_category="security_monitoring",
        )
