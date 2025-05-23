import requests # Added
import json     # Added
from typing import List, Dict, Any, Optional
from .base_provider import AbstractAIProvider
from config import console, OLLAMA_BASE_URL # Updated import

class OllamaProvider(AbstractAIProvider):
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        if not self.base_url:
            console.print("[bold red]Ollama base URL není nakonfigurováno. OllamaProvider nebude funkční.[/bold red]")
        # else:
            # console.print(f"OllamaProvider inicializován s base_url: {self.base_url}")

    def get_provider_name(self) -> str:
        return "Ollama (Local)"

    def load_models(self) -> List[Dict[str, Any]]:
        if not self.base_url:
            console.print(f"[{self.get_provider_name()}] Base URL není nastaveno, nelze načíst modely.")
            return []
        try:
            response = requests.get(f"{self.base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            
            formatted_models = []
            for model_info in models:
                model_name = model_info.get("name")
                if model_name: # Ujistíme se, že model má jméno
                    # Velikost v GB
                    size_gb = model_info.get('size', 0) / (1024**3)
                    formatted_models.append({
                        'id': model_name, # např. "llava:latest"
                        'name': model_name, # Pro TUI můžeme chtít zobrazit jen část před ':'
                        'description': f"Ollama local model (Modified: {model_info.get('modified_at', 'N/A')}, Size: {size_gb:.2f} GB)",
                        'free': True,
                        'price_input': None,
                        'price_output': None,
                        'context_window': None # Ollama modely mají různá okna, těžko určit obecně
                    })
            # console.print(f"[{self.get_provider_name()}] Načteno modelů: {formatted_models}")
            return formatted_models
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red][{self.get_provider_name()}] Chyba při načítání modelů z Ollama: {e}[/bold red]")
            return []
        except json.JSONDecodeError:
            console.print(f"[bold red][{self.get_provider_name()}] Chyba při parsování odpovědi modelů z Ollama.[/bold red]")
            return []

    def classify_image(
        self, model_id: str, image_b64: str, mime_type: str, 
        prompt_text: str, temperature: float = 0.2, **kwargs: Any
    ) -> Optional[str]:
        if not self.base_url:
            console.print(f"[{self.get_provider_name()}] Base URL není nastaveno.")
            return None

        current_prompt = prompt_text
        existing_tags = kwargs.get("existing_tags")
        if existing_tags and isinstance(existing_tags, list) and existing_tags:
            tags_text = ", ".join(existing_tags)
            tags_section_text = f"- Zde je seznam existujících tagů, které bys měl/a preferovat, pokud se hodí: [{tags_text}].\n"
            if "{{EXISTING_TAGS_SECTION}}\n" in current_prompt:
                current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", tags_section_text)
        else:
            current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", "")

        payload = {
            "model": model_id,
            "prompt": current_prompt,
            "images": [image_b64] if image_b64 else [],
            "stream": False,
            "options": {
                "temperature": temperature 
            }
            # "format": "json" # Pokud by model podporoval vynucení JSON výstupu
        }
        
        api_url = f"{self.base_url.rstrip('/')}/api/generate"
        # console.print(f"[{self.get_provider_name()}] Sending request to: {api_url} with model: {model_id}")

        try:
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            
            api_response_data = response.json()
            # console.print(f"[{self.get_provider_name()}] Raw API response data: {api_response_data}")
            
            generated_text_response = api_response_data.get("response")
            if generated_text_response:
                # console.print(f"[{self.get_provider_name()}] Generated text (expected JSON): {generated_text_response[:300]}...")
                return generated_text_response 
            else:
                # console.print(f"[bold red][{self.get_provider_name()}] 'response' field not found in Ollama API output.[/bold red]")
                # console.print(f"[bold red][{self.get_provider_name()}] Full API output: {api_response_data}[/bold red]")
                return None

        except requests.exceptions.RequestException as e:
            console.print(f"[bold red][{self.get_provider_name()}] Chyba při volání Ollama API: {e}[/bold red]")
            if e.response is not None:
                console.print(f"[bold red][{self.get_provider_name()}] API Response Text (chyba): {e.response.text[:500]}[/bold red]")
            return None
        except json.JSONDecodeError: 
            console.print(f"[bold red][{self.get_provider_name()}] Chyba při parsování hlavní JSON odpovědi od Ollama.[/bold red]")
            return None
