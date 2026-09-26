from pydantic import ValidationError

from app.ai.llm_client import (
    LLMClient,
    LLMClientError,
    create_llm_client,
)
from app.ai.prompts import (
    REQUIREMENT_EXTRACTION_SYSTEM_PROMPT,
    REQUIREMENT_EXTRACTION_USER_PROMPT,
)
from app.extraction.schemas import RequirementExtractionResult


class RequirementExtractionError(Exception):
    """Raised when RFP requirement extraction fails."""


class RequirementExtractor:
    """Extract structured requirements from RFP text using an LLM."""

    def __init__(self, llm_client: LLMClient | None = None):
        """
        Initialize the requirement extractor.

        Args:
            llm_client:
                Optional LLM client.

                If no client is supplied, the configured provider
                from the environment is created automatically.
        """

        self.llm_client = (
            llm_client
            if llm_client is not None
            else create_llm_client()
        )

    def extract(
        self,
        rfp_text: str,
    ) -> RequirementExtractionResult:
        """
        Extract structured requirements from RFP text.

        Args:
            rfp_text:
                Extracted text from an RFP document.

        Returns:
            Validated structured requirement data.

        Raises:
            ValueError:
                If the RFP text is empty.

            RequirementExtractionError:
                If extraction or validation fails.
        """

        if not rfp_text.strip():
            raise ValueError("RFP text cannot be empty.")

        prompt = (
            f"{REQUIREMENT_EXTRACTION_SYSTEM_PROMPT}\n\n"
            f"{REQUIREMENT_EXTRACTION_USER_PROMPT.format(
                rfp_text=rfp_text
            )}"
        )

        try:
            response = self.llm_client.generate(prompt)

        except LLMClientError as exc:
            raise RequirementExtractionError(
                f"LLM extraction failed: {exc}"
            ) from exc

        try:
            parsed_data = self._parse_json_response(response)

            result = RequirementExtractionResult.model_validate(
                parsed_data
            )

            result.total_requirements = len(
                result.requirements
            )

            return result

        except (
            ValueError,
            ValidationError,
            TypeError,
        ) as exc:
            raise RequirementExtractionError(
                f"Invalid structured response from LLM: {exc}"
            ) from exc

    @staticmethod
    def _parse_json_response(response: str) -> dict:
        """
        Parse JSON returned by the LLM.

        Handles:

        1. Plain JSON
        2. Markdown JSON code blocks
        """

        import json

        cleaned_response = response.strip()

        if cleaned_response.startswith("```"):
            lines = cleaned_response.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned_response = "\n".join(
                lines
            ).strip()

        return json.loads(cleaned_response)
