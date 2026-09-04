# backend/app/models_ai/ollama_provider.py
import json
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.models_ai.provider_base import ModelProvider

class OllamaProvider(ModelProvider):
    def __init__(self, base_url: str = "http://localhost:11434", timeout_s: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_s)
        
    async def generate(self, model: str, prompt: str, system: str = None, options: Dict[str, Any] = None, images: List[str] = None) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options
        if images:
            payload["images"] = images

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def generate_structured(self, model: str, prompt: str, schema: Dict[str, Any], system: str = None) -> Dict[str, Any]:
        # Ollama supports 'format': 'json'. For strict schemas, you prompt the schema.
        payload = {
            "model": model,
            "prompt": f"{prompt}\n\nYou must output valid JSON conforming to this schema:\n{json.dumps(schema)}",
            "stream": False,
            "format": "json"
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return json.loads(data.get("response", "{}"))
            except json.JSONDecodeError:
                return {"error": "Failed to parse JSON from model output"}

    async def embed(self, model: str, text: str) -> List[float]:
        payload = {
            "model": model,
            "prompt": text
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

    async def stream(self, model: str, prompt: str, system: str = None) -> AsyncGenerator[str, None]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]