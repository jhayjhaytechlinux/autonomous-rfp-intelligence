import pytest

from app.extraction.requirement_extractor import (
    RequirementExtractionError,
    RequirementExtractor,
)
from app.extraction.schemas import RequirementExtractionResult


class FakeLLMClient:
    """Fake LLM client for deterministic unit testing."""

    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str) -> str:
        """Return the predefined fake response."""
        return self.response


def test_requirement_extractor_parses_valid_json():
    """Verify valid LLM JSON is converted into the required schema."""

    response = """
    {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "category": "technical",
                "description": "Provide real-time security event monitoring.",
                "mandatory": true,
                "source_section": "Technical Requirements",
                "evidence": "Real-time security event monitoring."
            }
        ],
        "total_requirements": 1
    }
    """

    fake_client = FakeLLMClient(response)

    extractor = RequirementExtractor(
        llm_client=fake_client
    )

    result = extractor.extract(
        "The solution must provide real-time security event monitoring."
    )

    assert isinstance(
        result,
        RequirementExtractionResult,
    )

    assert result.total_requirements == 1

    assert (
        result.requirements[0].requirement_id
        == "REQ-001"
    )

    assert (
        result.requirements[0].category.value
        == "technical"
    )


def test_requirement_extractor_rejects_empty_text():
    """Verify empty RFP text is rejected."""

    fake_client = FakeLLMClient("{}")

    extractor = RequirementExtractor(
        llm_client=fake_client
    )

    with pytest.raises(ValueError):
        extractor.extract("")


def test_requirement_extractor_rejects_invalid_json():
    """Verify malformed LLM output is rejected."""

    fake_client = FakeLLMClient(
        "This is not valid JSON."
    )

    extractor = RequirementExtractor(
        llm_client=fake_client
    )

    with pytest.raises(RequirementExtractionError):
        extractor.extract("Sample RFP text.")


def test_requirement_extractor_handles_markdown_json():
    """Verify JSON inside Markdown code blocks is accepted."""

    response = """
    ```json
    {
        "requirements": [
            {
                "requirement_id": "REQ-001",
                "category": "experience",
                "description": "Demonstrate cybersecurity experience.",
                "mandatory": true,
                "source_section": "Experience Requirements",
                "evidence": "At least 3 years cybersecurity experience."
            }
        ],
        "total_requirements": 1
    }
    ```
    """

    fake_client = FakeLLMClient(response)

    extractor = RequirementExtractor(
        llm_client=fake_client
    )

    result = extractor.extract(
        "At least 3 years cybersecurity experience."
    )

    assert result.total_requirements == 1

    assert (
        result.requirements[0].category.value
        == "experience"
    )
