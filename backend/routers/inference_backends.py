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


class ClaudeBackend(InferenceBackend):
    """Claude inference supporting both native Anthropic API and OpenAI-compatible endpoints."""

    def __init__(self):
        self.base_url = os.getenv("CLAUDE_BASE_URL")
        self.api_key = os.getenv("CLAUDE_API_KEY")
        self.model = os.getenv("CLAUDE_MODEL")
        
        # Auto-detect endpoint type or use explicit configuration
        # CLAUDE_API_TYPE: "anthropic" (native) or "openai" (compatible)
        api_type = os.getenv("CLAUDE_API_TYPE", "").lower()
        
        if api_type == "anthropic":
            self.use_native_api = True
        elif api_type == "openai":
            self.use_native_api = False
        else:
            # Auto-detect: if URL contains anthropic.com, use native API
            self.use_native_api = "anthropic.com" in (self.base_url or "")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream using native Anthropic API or OpenAI-compatible endpoint."""
        if not self.base_url:
            raise ValueError("CLAUDE_BASE_URL not set")
        if not self.api_key:
            raise ValueError("CLAUDE_API_KEY not set")
        if not self.model:
            raise ValueError("CLAUDE_MODEL not set")

        if self.use_native_api:
            async for token in self._stream_native_api(messages):
                yield token
        else:
            async for token in self._stream_openai_compatible(messages):
                yield token

    async def _stream_native_api(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream using native Anthropic Messages API (/v1/messages)."""
        import json
        
        # Normalize base URL (strip trailing slash)
        base_url = self.base_url.rstrip("/")
        endpoint = f"{base_url}/v1/messages"
        
        # Convert OpenAI format to Anthropic format
        # Anthropic requires system message separate from conversation
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Build request body
        request_body = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 2048,
            "temperature": 0.7,
            "stream": True,
        }
        
        if system_message:
            request_body["system"] = system_message
        
        async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=request_body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    
                    try:
                        chunk = json.loads(data)
                        
                        # Handle different event types
                        if chunk.get("type") == "content_block_delta":
                            delta = chunk.get("delta", {})
                            if delta.get("type") == "text_delta":
                                if token := delta.get("text"):
                                    yield token
                        elif chunk.get("type") == "message_stop":
                            break
                            
                    except (json.JSONDecodeError, KeyError):
                        continue

    async def _stream_openai_compatible(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream using OpenAI-compatible /chat/completions endpoint."""
        import json
        
        # Normalize base URL (strip trailing slash)
        base_url = self.base_url.rstrip("/")
        endpoint = f"{base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
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
                        try:
                            chunk = json.loads(data)
                            if token := chunk["choices"][0]["delta"].get("content"):
                                yield token
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue


# Backend factory
def get_backend() -> InferenceBackend:
    """Get inference backend based on INFERENCE_PROVIDER env var."""
    provider = os.getenv("INFERENCE_PROVIDER", "ollama")
    
    backends = {
        "ollama": OllamaBackend,
        "gemini": GeminiBackend,
        "vllm": VLLMBackend,
        "openai": OpenAIBackend,
        "claude": ClaudeBackend,
    }
    
    if provider not in backends:
        raise ValueError(
            f"Unknown INFERENCE_PROVIDER={provider}. "
            f"Supported: {', '.join(backends.keys())}"
        )
    
    return backends[provider]()
