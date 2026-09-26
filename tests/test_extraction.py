from app.extraction.schemas import (
    Requirement,
    RequirementCategory,
    RequirementExtractionResult,
)


def test_requirement_schema():
    """Verify that a requirement can be created successfully."""

    requirement = Requirement(
        requirement_id="REQ-001",
        category=RequirementCategory.TECHNICAL,
        description="Provide real-time security event monitoring",
        mandatory=True,
        source_section="Technical Requirements",
        evidence=(
            "The solution must provide real-time security event monitoring."
        ),
    )

    assert requirement.requirement_id == "REQ-001"
    assert requirement.category == RequirementCategory.TECHNICAL
    assert requirement.mandatory is True


def test_requirement_extraction_result():
    """Verify the extraction result container."""

    requirement = Requirement(
        requirement_id="REQ-001",
        category=RequirementCategory.EXPERIENCE,
        description="Demonstrate cybersecurity experience",
        mandatory=True,
        source_section="Experience Requirements",
        evidence="At least 3 years of cybersecurity experience.",
    )

    result = RequirementExtractionResult(
        requirements=[requirement],
        total_requirements=1,
    )

    assert len(result.requirements) == 1
    assert result.total_requirements == 1


def test_requirement_category_values():
    """Verify the supported requirement categories."""

    categories = {category.value for category in RequirementCategory}

    assert "technical" in categories
    assert "experience" in categories
    assert "personnel" in categories
    assert "commercial" in categories
    assert "implementation" in categories
    assert "training" in categories
    assert "legal" in categories
    assert "submission" in categories
