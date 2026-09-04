# backend/app/models_ai/provider_base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, List

class ModelProvider(ABC):
    """
    Abstract interface for LLM providers.
    Ensures the system is decoupled from specific implementations like Ollama or vLLM.
    """
    
    @abstractmethod
    async def generate(self, model: str, prompt: str, system: str = None, options: Dict[str, Any] = None) -> str:
        """Generate a standard text completion."""
        pass

    @abstractmethod
    async def generate_structured(self, model: str, prompt: str, schema: Dict[str, Any], system: str = None) -> Dict[str, Any]:
        """Generate output conforming to a specific JSON schema."""
        pass

    @abstractmethod
    async def embed(self, model: str, text: str) -> List[float]:
        """Generate a vector embedding for the given text."""
        pass

    @abstractmethod
    async def stream(self, model: str, prompt: str, system: str = None) -> AsyncGenerator[str, None]:
        """Stream the generation response back chunk by chunk."""
        pass