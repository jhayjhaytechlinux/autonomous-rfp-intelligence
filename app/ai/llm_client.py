import os
from abc import ABC, abstractmethod

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


class LLMClientError(Exception):
    """Raised when communication with an LLM provider fails."""


class LLMClient(ABC):
    """Provider-independent interface for language model clients."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt for the language model.

        Returns:
            Generated response text.
        """
        raise NotImplementedError


class GeminiClient(LLMClient):
    """Client for interacting with the Google Gemini API."""

    def __init__(
        self,
        model: str = "gemini-3.1-flash-lite",
        api_key: str | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise LLMClientError(
                "GEMINI_API_KEY is not configured."
            )

        try:
            self.client = genai.Client(
                api_key=self.api_key
            )
        except Exception as exc:
            raise LLMClientError(
                f"Unable to initialize Gemini client: {exc}"
            ) from exc

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the generated response.

        Args:
            prompt: Input prompt.

        Returns:
            Generated response text.

        Raises:
            ValueError: If the prompt is empty.
            LLMClientError: If Gemini communication fails.
        """

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )

        except Exception as exc:
            raise LLMClientError(
                f"Unable to communicate with Gemini: {exc}"
            ) from exc

        generated_text = getattr(
            response,
            "text",
            None,
        )

        if not generated_text:
            raise LLMClientError(
                "Gemini returned an empty response."
            )

        return generated_text.strip()


class OllamaClient(LLMClient):
    """Client for interacting with a local Ollama server."""

    def __init__(
        self,
        host: str = "http://127.0.0.1:11434",
        model: str = "phi3:mini",
        timeout: float = 180.0,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Ollama and return the generated response.

        Args:
            prompt: Input prompt.

        Returns:
            Generated response text.

        Raises:
            ValueError: If the prompt is empty.
            LLMClientError: If Ollama communication fails.
        """

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except httpx.TimeoutException as exc:
            raise LLMClientError(
                f"Ollama request timed out after "
                f"{self.timeout} seconds."
            ) from exc

        except httpx.HTTPError as exc:
            raise LLMClientError(
                f"Unable to communicate with Ollama: {exc}"
            ) from exc

        try:
            data = response.json()

        except ValueError as exc:
            raise LLMClientError(
                "Ollama returned invalid JSON."
            ) from exc

        generated_text = data.get("response")

        if not generated_text:
            raise LLMClientError(
                "Ollama returned an empty response."
            )

        return generated_text.strip()


def create_llm_client() -> LLMClient:
    """
    Create an LLM client based on AI_PROVIDER.

    Supported providers:
        - gemini
        - ollama
    """

    provider = os.getenv(
        "AI_PROVIDER",
        "gemini",
    ).strip().lower()

    model = os.getenv(
        "AI_MODEL",
        "gemini-3.1-flash-lite",
    ).strip()

    if provider == "gemini":
        return GeminiClient(
            model=model,
        )

    if provider == "ollama":
        ollama_host = os.getenv(
            "OLLAMA_HOST",
            "http://127.0.0.1:11434",
        )

        return OllamaClient(
            host=ollama_host,
            model=model,
        )

    raise ValueError(
        f"Unsupported AI provider: {provider}"
    )
