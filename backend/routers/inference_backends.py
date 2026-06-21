"""
Multi-backend inference abstraction layer.
Inspired by vLLM's unified interface for multiple model providers.
"""
import os
from abc import ABC, abstractmethod
from typing import AsyncIterator

import httpx


class InferenceBackend(ABC):
    """Abstract base for inference backends."""

    @abstractmethod
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream chat completions token by token."""
        ...


class OllamaBackend(InferenceBackend):
    """Ollama local inference."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        self.model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        import json
                        chunk = json.loads(line)
                        if token := chunk.get("message", {}).get("content"):
                            yield token


class GeminiBackend(InferenceBackend):
    """Google Gemini cloud inference."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)

        # Convert to Gemini format: "user"/"assistant"/"system" -> "user"/"model"
        def convert_role(role: str) -> str:
            if role == "assistant":
                return "model"
            # Both "user" and "system" map to "user" in Gemini
            return "user"

        history = [{"role": convert_role(m["role"]), "parts": [m["content"]]} 
                   for m in messages[:-1]]
        prompt = messages[-1]["content"]

        chat = model.start_chat(history=history)
        response = chat.send_message(prompt, stream=True)

        for chunk in response:
            if chunk.text:
                yield chunk.text


class VLLMBackend(InferenceBackend):
    """vLLM server inference with OpenAI-compatible API."""

    def __init__(self):
        self.base_url = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
        self.model = os.getenv("VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
        self.api_key = os.getenv("VLLM_API_KEY", "EMPTY")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream using vLLM's OpenAI-compatible /v1/chat/completions endpoint."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            if token := chunk["choices"][0]["delta"].get("content"):
                                yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue


class OpenAIBackend(InferenceBackend):
    """OpenAI cloud inference."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self.api_key)

        stream = await client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            if token := chunk.choices[0].delta.content:
                yield token


# Backend factory
def get_backend() -> InferenceBackend:
    """Get inference backend based on INFERENCE_PROVIDER env var."""
    provider = os.getenv("INFERENCE_PROVIDER", "ollama")
    
    backends = {
        "ollama": OllamaBackend,
        "gemini": GeminiBackend,
        "vllm": VLLMBackend,
        "openai": OpenAIBackend,
    }
    
    if provider not in backends:
        raise ValueError(
            f"Unknown INFERENCE_PROVIDER={provider}. "
            f"Supported: {', '.join(backends.keys())}"
        )
    
    return backends[provider]()
