from pathlib import Path

import pytest

from app.compliance.capability_loader import (
    CapabilityProfileLoadError,
    load_capability_profile,
)


CAPABILITY_FILE = Path(
    "data/capabilities/secureops_africa.json"
)


def test_load_secureops_africa_profile():
    profile = load_capability_profile(CAPABILITY_FILE)

    assert profile.company_name == "SecureOps Africa"
    assert profile.company_type == "Cybersecurity Services Provider"
    assert len(profile.capabilities) == 14


def test_loaded_capabilities_have_unique_ids():
    profile = load_capability_profile(CAPABILITY_FILE)

    capability_ids = [
        capability.capability_id
        for capability in profile.capabilities
    ]

    assert len(capability_ids) == len(set(capability_ids))


def test_missing_capability_profile():
    with pytest.raises(CapabilityProfileLoadError):
        load_capability_profile(
            "data/capabilities/does-not-exist.json"
        )


def test_non_json_capability_profile():
    with pytest.raises(CapabilityProfileLoadError):
        load_capability_profile(
            "data/capabilities/secureops_africa.txt"
        )
