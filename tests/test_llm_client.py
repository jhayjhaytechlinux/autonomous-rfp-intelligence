import pytest

from app.ai.llm_client import (
    GeminiClient,
    LLMClient,
    LLMClientError,
    OllamaClient,
    create_llm_client,
)


def test_gemini_client_implements_llm_client():
    """Verify that GeminiClient uses the provider interface."""

    client = GeminiClient(
        api_key="test-key",
    )

    assert isinstance(client, LLMClient)


def test_ollama_client_implements_llm_client():
    """Verify that OllamaClient uses the provider interface."""

    client = OllamaClient()

    assert isinstance(client, LLMClient)


def test_empty_prompt_is_rejected_by_gemini():
    """Verify that Gemini rejects an empty prompt."""

    client = GeminiClient(
        api_key="test-key",
    )

    with pytest.raises(ValueError):
        client.generate("")


def test_whitespace_prompt_is_rejected_by_gemini():
    """Verify that Gemini rejects whitespace-only prompts."""

    client = GeminiClient(
        api_key="test-key",
    )

    with pytest.raises(ValueError):
        client.generate("   ")


def test_empty_prompt_is_rejected_by_ollama():
    """Verify that Ollama rejects an empty prompt."""

    client = OllamaClient()

    with pytest.raises(ValueError):
        client.generate("")


def test_whitespace_prompt_is_rejected_by_ollama():
    """Verify that Ollama rejects whitespace-only prompts."""

    client = OllamaClient()

    with pytest.raises(ValueError):
        client.generate("   ")


def test_ollama_client_configuration():
    """Verify the default Ollama configuration."""

    client = OllamaClient()

    assert client.host == "http://127.0.0.1:11434"
    assert client.model == "phi3:mini"
    assert client.timeout == 180.0


def test_gemini_client_configuration():
    """Verify Gemini configuration."""

    client = GeminiClient(
        model="gemini-3.1-flash-lite",
        api_key="test-key",
    )

    assert client.model == "gemini-3.1-flash-lite"
    assert client.api_key == "test-key"


def test_llm_client_is_abstract():
    """Verify the base LLM client cannot be instantiated directly."""

    with pytest.raises(TypeError):
        LLMClient()


def test_llm_client_error_is_exception():
    """Verify LLMClientError behaves like an exception."""

    error = LLMClientError("Test error")

    assert isinstance(error, Exception)


def test_create_gemini_client(monkeypatch):
    """Verify the provider factory creates GeminiClient."""

    monkeypatch.setenv(
        "AI_PROVIDER",
        "gemini",
    )

    monkeypatch.setenv(
        "AI_MODEL",
        "gemini-3.1-flash-lite",
    )

    monkeypatch.setenv(
        "GEMINI_API_KEY",
        "test-key",
    )

    client = create_llm_client()

    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-3.1-flash-lite"


def test_create_ollama_client(monkeypatch):
    """Verify the provider factory creates OllamaClient."""

    monkeypatch.setenv(
        "AI_PROVIDER",
        "ollama",
    )

    monkeypatch.setenv(
        "AI_MODEL",
        "phi3:mini",
    )

    monkeypatch.setenv(
        "OLLAMA_HOST",
        "http://127.0.0.1:11434",
    )

    client = create_llm_client()

    assert isinstance(client, OllamaClient)
    assert client.model == "phi3:mini"


def test_create_llm_client_rejects_unknown_provider(monkeypatch):
    """Verify unsupported providers are rejected."""

    monkeypatch.setenv(
        "AI_PROVIDER",
        "unknown-provider",
    )

    with pytest.raises(ValueError):
        create_llm_client()
