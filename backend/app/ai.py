import json
import logging

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Thin async client for a locally hosted Ollama server."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model

    async def list_models(self) -> list[str] | None:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
                return [m.get("name", "") for m in payload.get("models", [])]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ollama not reachable at %s: %s", self.base_url, exc)
            return None

    async def available(self) -> bool:
        models = await self.list_models()
        if models is None:
            return False
        return any(self.model.split(":")[0] in m for m in models)

    async def chat_json(self, system: str, user: str) -> dict | None:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_predict": settings.ai_max_tokens,
                "num_ctx": 2048,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return json.loads(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama chat failed (%s): %s", self.base_url, exc)
            return None


ollama = OllamaClient()
