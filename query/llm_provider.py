"""
LLM provider abstraction for the Graph RAG query layer (Phase 3).

query/rag.py needs exactly one capability from an LLM: given a prompt
(optionally with a system instruction), return text. `LLMProvider` is
that single-method interface, so rag.py's prompt-construction and
system-prompt logic never has to know which vendor's SDK sits
underneath. See docs/decisions/004-llm-provider-abstraction.md for why
this exists now, ahead of an actual second provider being wired up.

Adding a new provider is meant to be a five-minute job, not a rewrite -
see CLAUDE.md's "Adding an LLM Provider" section for the checklist:
implement `LLMProvider`, register it in `PROVIDERS` below, done.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

import anthropic
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    """A vendor-agnostic text-generation adapter. One method, deliberately:
    the query layer only ever needs "send this prompt, get text back" -
    everything vendor-specific (model choice, reasoning/thinking config,
    retries, auth) is the provider implementation's problem, not the
    caller's."""

    @abstractmethod
    def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Sends `prompt` (with an optional `system` instruction) to the
        provider's model and returns the text response. Implementations
        must raise on failure rather than returning a placeholder or
        fabricated string in place of a real answer."""
        raise NotImplementedError


class ClaudeProvider(LLMProvider):
    """Anthropic Claude, via the official SDK - see .claude/skills's
    claude-api skill for the conventions this follows (model ID,
    adaptive thinking, refusal handling). The working default provider
    for this project."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
        self._client = anthropic.Anthropic()

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        response = self._client.messages.create(**kwargs)

        if response.stop_reason == "refusal":
            raise RuntimeError(
                "Claude declined to answer (safety classifier refusal) - "
                f"stop_details: {response.stop_details}"
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text:
            raise RuntimeError(f"No text content in response (stop_reason={response.stop_reason})")
        return text


class OpenAIProvider(LLMProvider):
    """Not implemented - no OPENAI_API_KEY is configured for this project
    yet. Stubbed so the interface and PROVIDERS registry are complete;
    implementing this is limited to installing the `openai` package and
    filling in generate() (chat.completions.create or the Responses API)
    once a key exists - see CLAUDE.md's "Adding an LLM Provider"."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OPENAI_MODEL")

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError(
            "OpenAIProvider is a stub - no OPENAI_API_KEY is configured for "
            "this project. Implement generate() with the `openai` SDK once "
            "a key is available; see CLAUDE.md's 'Adding an LLM Provider'."
        )


class KimiProvider(LLMProvider):
    """Not implemented - no Moonshot/Kimi API key is configured for this
    project yet. Stubbed for the same reason as OpenAIProvider. Kimi's
    API is OpenAI-compatible, so implementing this is likely a copy of
    OpenAIProvider pointed at Moonshot's base URL once a key exists -
    see CLAUDE.md's "Adding an LLM Provider"."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("KIMI_MODEL")

    def generate(self, prompt: str, *, system: str | None = None) -> str:
        raise NotImplementedError(
            "KimiProvider is a stub - no Kimi/Moonshot API key is "
            "configured for this project. Implement generate() with an "
            "OpenAI-compatible client pointed at Moonshot's base URL once "
            "a key is available; see CLAUDE.md's 'Adding an LLM Provider'."
        )


PROVIDERS: dict[str, type[LLMProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "kimi": KimiProvider,
}


def get_provider(name: str | None = None) -> LLMProvider:
    """Looks up a provider by name (default: `LLM_PROVIDER` env var, or
    "claude" if that's unset too). Raises KeyError with the valid
    options if `name` isn't registered."""
    name = name or os.environ.get("LLM_PROVIDER", "claude")
    if name not in PROVIDERS:
        raise KeyError(f"Unknown provider {name!r} - choices: {sorted(PROVIDERS)}")
    return PROVIDERS[name]()
