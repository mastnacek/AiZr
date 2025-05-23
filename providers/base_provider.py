from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class AbstractAIProvider(ABC):
    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def load_models(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def classify_image(
        self,
        model_id: str,
        image_b64: str,
        mime_type: str,
        prompt_text: str,
        temperature: float = 0.2,
        **kwargs: Any
    ) -> Optional[str]:
        pass

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        pass
