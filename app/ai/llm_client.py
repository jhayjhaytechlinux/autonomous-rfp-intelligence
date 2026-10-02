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
    """
    Client for interacting with the Google Gemini API.

    Gemini remains the primary provider because it is significantly
    faster for this project than the local Ollama fallback.

    If Gemini experiences a temporary service-availability problem,
    an optional fallback LLM client can be used automatically.
    """

    def __init__(
        self,
        model: str = "gemini-3.1-flash-lite",
        api_key: str | None = None,
        fallback_client: LLMClient | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.fallback_client = fallback_client

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

    @staticmethod
    def _is_temporary_provider_error(error: Exception) -> bool:
        """
        Determine whether an error looks like a temporary Gemini
        availability/rate-limit problem where fallback is appropriate.

        We deliberately do not fallback for configuration or programming
        errors such as an invalid API key.
        """

        message = str(error).lower()

        temporary_indicators = (
            "503",
            "service unavailable",
            "unavailable",
            "high demand",
            "temporarily unavailable",
            "temporarily overloaded",
            "429",
            "resource exhausted",
            "rate limit",
            "too many requests",
            "internal server error",
            "500",
            "deadline exceeded",
            "timeout",
            "timed out",
        )

        return any(
            indicator in message
            for indicator in temporary_indicators
        )

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to Gemini and return the generated response.

        If Gemini temporarily fails and a fallback client is configured,
        the request is automatically sent to the fallback provider.

        Args:
            prompt: Input prompt.

        Returns:
            Generated response text.

        Raises:
            ValueError:
                If the prompt is empty.
            LLMClientError:
                If Gemini fails and fallback is unavailable or also fails.
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
            gemini_error = LLMClientError(
                f"Unable to communicate with Gemini: {exc}"
            )

            # Only use Ollama for temporary Gemini availability problems.
            if (
                self.fallback_client is not None
                and self._is_temporary_provider_error(exc)
            ):
                try:
                    print(
                        "⚠️ Gemini temporarily unavailable. "
                        "Falling back to Ollama..."
                    )

                    return self.fallback_client.generate(prompt)

                except Exception as fallback_exc:
                    raise LLMClientError(
                        "Gemini was temporarily unavailable and "
                        f"Ollama fallback also failed: {fallback_exc}"
                    ) from fallback_exc

            raise gemini_error from exc

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
            ValueError:
                If the prompt is empty.
            LLMClientError:
                If Ollama communication fails.
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
    Create the configured LLM client.

    Supported providers:
        - gemini
        - ollama

    Gemini is the normal primary provider.

    When AI_PROVIDER=gemini, Ollama is automatically configured as
    a fallback for temporary Gemini availability problems.

    Environment variables:

        AI_PROVIDER
            Primary provider. Default: gemini

        AI_MODEL
            Gemini model. Default: gemini-3.1-flash-lite

        OLLAMA_HOST
            Ollama server URL.
            Default: http://127.0.0.1:11434

        OLLAMA_MODEL
            Ollama fallback model.
            Default: phi3:mini

        OLLAMA_TIMEOUT
            Ollama timeout in seconds.
            Default: 180
    """

    provider = os.getenv(
        "AI_PROVIDER",
        "gemini",
    ).strip().lower()

    gemini_model = os.getenv(
        "AI_MODEL",
        "gemini-3.1-flash-lite",
    ).strip()

    ollama_host = os.getenv(
        "OLLAMA_HOST",
        "http://127.0.0.1:11434",
    ).strip()

    ollama_model = os.getenv(
        "OLLAMA_MODEL",
        "phi3:mini",
    ).strip()

    try:
        ollama_timeout = float(
            os.getenv(
                "OLLAMA_TIMEOUT",
                "180",
            )
        )

    except ValueError as exc:
        raise ValueError(
            "OLLAMA_TIMEOUT must be a valid number."
        ) from exc

    if provider == "gemini":
        fallback_client = OllamaClient(
            host=ollama_host,
            model=ollama_model,
            timeout=ollama_timeout,
        )

        return GeminiClient(
            model=gemini_model,
            fallback_client=fallback_client,
        )

    if provider == "ollama":
        return OllamaClient(
            host=ollama_host,
            model=ollama_model,
            timeout=ollama_timeout,
        )

    raise ValueError(
        f"Unsupported AI provider: {provider}"
    )
