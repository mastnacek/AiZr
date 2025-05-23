from typing import List, Dict, Any, Optional
from .base_provider import AbstractAIProvider
from config import GOOGLE_GEMINI_API_KEY, console

class GoogleGeminiProvider(AbstractAIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_GEMINI_API_KEY
        if not self.api_key:
            console.print("[yellow]Google Gemini API klíč není nastaven. GoogleGeminiProvider nebude funkční.[/yellow]")

    def get_provider_name(self) -> str:
        return "Google Gemini (Direct)"

    def load_models(self) -> List[Dict[str, Any]]:
        console.print(f"[{self.get_provider_name()}] load_models() není implementováno.")
        raise NotImplementedError
        return []

    def classify_image(
        self, model_id: str, image_b64: str, mime_type: str, 
        prompt_text: str, temperature: float = 0.2, **kwargs: Any
    ) -> Optional[str]:
        if not self.api_key:
            console.print(f"[{self.get_provider_name()}] API klíč není nastaven.")
            return None
        console.print(f"[{self.get_provider_name()}] classify_image() není implementováno.")
        raise NotImplementedError
        return None
