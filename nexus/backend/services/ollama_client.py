import json
from typing import AsyncIterator, Optional

import httpx

from backend.config import settings


class OllamaClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self._client = httpx.AsyncClient(timeout=90.0)

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/api/tags")
            return r.status_code == 200
        except Exception:
            return False

    async def model_available(self, model: str) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/api/tags")
            if r.status_code != 200:
                return False
            tags = r.json()
            return any(m["name"].startswith(model) for m in tags.get("models", []))
        except Exception:
            return False

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> tuple[str, int, int]:
        """Returns (response_text, prompt_tokens, response_tokens)."""
        payload: dict = {
            "model": model or settings.worker_model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        r = await self._client.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=settings.worker_timeout,
        )
        r.raise_for_status()
        data = r.json()
        return (
            data["response"],
            data.get("prompt_eval_count", 0),
            data.get("eval_count", 0),
        )

    async def stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> AsyncIterator[tuple[str, Optional[int], Optional[int]]]:
        """
        Yields (chunk, None, None) per chunk.
        Final yield is ("", prompt_tokens, response_tokens).
        """
        payload: dict = {
            "model": model or settings.manager_model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        async with self._client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=settings.worker_timeout,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                chunk = data.get("response", "")
                if data.get("done"):
                    yield chunk, data.get("prompt_eval_count"), data.get("eval_count")
                else:
                    yield chunk, None, None

    async def close(self):
        await self._client.aclose()
