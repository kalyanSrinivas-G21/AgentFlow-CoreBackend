# backend/app/models_ai/ollama_provider.py
import json
import httpx
from typing import AsyncGenerator, Dict, Any, List
from app.models_ai.provider_base import ModelProvider
from app.models_ai.resource_manager import GPUResourceManager, ResourceExhaustedError

class OllamaProvider(ModelProvider):
    def __init__(self, base_url: str = "http://localhost:11434", timeout_s: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = httpx.Timeout(timeout_s)
        self.resource_manager = GPUResourceManager()
        
    def _enforce_context_budget(self, prompt: str) -> str:
        """Step 9.5: Context/Token Budget Control. Prevent massive prompts from blowing up KV cache VRAM."""
        max_chars = 12000 # Rough proxy for ~3000 tokens
        if len(prompt) > max_chars:
            return prompt[:max_chars] + "\n...[TRUNCATED BY RESOURCE MANAGER TO PREVENT VRAM EXHAUSTION]"
        return prompt

    async def generate(self, model: str, prompt: str, system: str = None, options: Dict[str, Any] = None, images: List[str] = None) -> str:
        
        # Step 9.5: Truncate prompt
        safe_prompt = self._enforce_context_budget(prompt)
        
        # Step 9.2: Intercept execution via NVML Admission Control
        try:
            await self.resource_manager.admit(model, self.base_url)
        except ResourceExhaustedError as e:
            # By returning this specific payload, the TaskRunner or Graph logic will catch it 
            # and naturally retry, acting as back-pressure.
            raise Exception(str(e))
            
        try:
            payload = {
                "model": model,
                "prompt": safe_prompt,
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
        finally:
            await self.resource_manager.release()

    async def generate_structured(self, model: str, prompt: str, schema: Dict[str, Any], system: str = None) -> Dict[str, Any]:
        safe_prompt = self._enforce_context_budget(prompt)
        
        await self.resource_manager.admit(model, self.base_url)
        try:
            payload = {
                "model": model,
                "prompt": f"{safe_prompt}\n\nYou must output valid JSON conforming to this schema:\n{json.dumps(schema)}",
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
        finally:
            await self.resource_manager.release()

    async def embed(self, model: str, text: str) -> List[float]:
        # Embeddings are typically small models, but we still route them through the manager
        await self.resource_manager.admit(model, self.base_url)
        try:
            payload = {
                "model": model,
                "prompt": text
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [])
        finally:
            await self.resource_manager.release()

    async def stream(self, model: str, prompt: str, system: str = None) -> AsyncGenerator[str, None]:
        safe_prompt = self._enforce_context_budget(prompt)
        
        await self.resource_manager.admit(model, self.base_url)
        try:
            payload = {
                "model": model,
                "prompt": safe_prompt,
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
        finally:
            await self.resource_manager.release()