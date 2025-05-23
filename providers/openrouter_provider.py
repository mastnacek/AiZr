import requests
import json
import re
from typing import List, Dict, Any, Optional

# Importy z projektu
from .base_provider import AbstractAIProvider # Relativní import
# Použijeme API_KEY z configu a přejmenujeme ho pro jasnost v tomto kontextu,
# nebo pokud by config obsahoval více klíčů.
# Nyní importujeme přímo přejmenovaný klíč z config.py
from config import console, OPENROUTER_API_KEY

# Pomocná funkce pro extrakci JSON (původní z api_client.py)
def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    # Stávající logování vstupu
    if text:
        console.print(f"[OpenRouterProvider DEBUG extract_json_from_text input text (first 500 chars)]: {text[:500]}")
    else:
        console.print("[OpenRouterProvider DEBUG extract_json_from_text input text]: Prázdný vstup.")
        return None

    json_str_match = None
    # Prioritize specific markdown block
    match_md = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if match_md:
        json_str_match = match_md.group(1)
    else:
        # Fallback to general JSON object search
        match_general = re.search(r"(\{.*\})", text, re.DOTALL)
        if match_general:
            json_str_match = match_general.group(1)

    if json_str_match:
        json_str = json_str_match.strip() # Odstranění bílých znaků kolem JSON bloku
        console.print(f"[OpenRouterProvider DEBUG Extracted json_str (first 500 chars after strip)]: {json_str[:500]}")
        try:
            data = json.loads(json_str)
            
            # --- Nové detailní logování po json.loads() ---
            console.print(f"[OpenRouterProvider DEBUG Parsed JSON type]: {type(data)}")
            if isinstance(data, dict):
                console.print(f"[OpenRouterProvider DEBUG Parsed JSON keys]: {list(data.keys())}")
                if "kategorie" in data:
                    console.print(f"[OpenRouterProvider DEBUG Type of 'kategorie' value]: {type(data['kategorie'])}")
                    console.print(f"[OpenRouterProvider DEBUG Value of 'kategorie']: {data['kategorie']}")
                    # Kontrola reprezentace klíčů
                    console.print(f"[OpenRouterProvider DEBUG Keys comparison]:")
                    for key_item in data.keys():
                        console.print(f"  Key: '{repr(key_item)}', Type: {type(key_item)}, Matches 'kategorie': {key_item == 'kategorie'}")
                else:
                    console.print("[OpenRouterProvider DEBUG 'kategorie' key NOT FOUND in parsed JSON data]")
            # --- Konec nového detailního logování ---

            if not isinstance(data, dict):
                console.print(f"[red]extract_json_from_text: Naparsovaná data nejsou slovník: {type(data)}[/red]")
                console.print(f"[OpenRouterProvider DEBUG Original text for non-dict data (first 500 chars)]: {text[:500]}")
                return None
            
            # Stávající kontrola klíče "kategorie"
            # Zde je podezření na problém, proto tolik logování výše
            if "kategorie" not in data or not isinstance(data.get("kategorie"), list):
                console.print("[red]extract_json_from_text: JSON neobsahuje klíč 'kategorie' s listem hodnot (dle standardní kontroly).[/red]")
                console.print(f"[OpenRouterProvider DEBUG Original text for missing 'kategorie' (first 500 chars)]: {text[:500]}")
                return None
            
            return data # Úspěšné parsování a validace

        except json.JSONDecodeError as e:
            error_snippet = json_str[:500] + "..." if len(json_str) > 500 else json_str
            console.print(f"[red]extract_json_from_text: Chyba při parsování JSON: {e}[/red]")
            console.print(f"[red]extract_json_from_text: Problematický JSON string (začátek): {error_snippet}[/red]")
            console.print(f"[OpenRouterProvider DEBUG Original text that failed JSON parsing (first 500 chars)]: {text[:500]}")
            return None
    else:
        console.print("[yellow]extract_json_from_text: JSON blok nenalezen v odpovědi API.[/yellow]")
        # Nyní se loguje celý vstupní text, pokud regex selže
        console.print(f"[OpenRouterProvider DEBUG Original text when no JSON block found (first 500 chars)]: {text[:500]}")
        return None

class OpenRouterProvider(AbstractAIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENROUTER_API_KEY 
        if not self.api_key:
            # Tato hláška by se neměla objevit, pokud config.py vynucuje OPENROUTER_API_KEY
            console.print("[bold red]OpenRouter API klíč nebyl poskytnut ani nalezen v konfiguraci! Klient nemusí fungovat.[/bold red]")
            # V produkci by zde mohla být vyhozena chyba: raise ValueError("OpenRouter API klíč je vyžadován.")

    def get_provider_name(self) -> str:
        return "OpenRouter"

    def load_models(self) -> List[Dict[str, Any]]:
        # Statický seznam modelů, jak je uvedeno v zadání
        return [
            {
                'id': 'google/gemini-2.5-flash-preview', 
                'name': 'Google Gemini 2.5 Flash Preview (via OpenRouter)',
                'description': 'Experimentální model od Google, rychlý a schopný.',
                'free': True, 
                'price_input': None,
                'price_output': None,
                'context_window': None 
            }
        ]

    def classify_image(
        self,
        model_id: str,
        image_b64: str,
        mime_type: str,
        prompt_text: str,
        temperature: float = 0.2,
        **kwargs: Any 
    ) -> Optional[str]:
        if not self.api_key:
            console.print("[bold red]OpenRouter API klíč není nastaven. Nelze pokračovat v klasifikaci.[/bold red]")
            return None

        current_prompt = prompt_text
        existing_tags = kwargs.get("existing_tags")
        if existing_tags and isinstance(existing_tags, list) and existing_tags: # Ensure existing_tags is not empty
            tags_text = ", ".join(existing_tags)
            tags_section_text = f"- Zde je seznam existujících tagů, které bys měl/a preferovat, pokud se hodí: [{tags_text}].\n"
            # Ensure the placeholder exists before replacing
            if "{{EXISTING_TAGS_SECTION}}\n" in current_prompt:
                 current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", tags_section_text)
            # else: # Optional: log if placeholder is missing
                 # console.print("[yellow]Placeholder {{EXISTING_TAGS_SECTION}} nenalezen v promptu.[/yellow]")
        else: # Remove placeholder if no tags or placeholder not found
            current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", "")
        
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": current_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                        }
                    ]
                }
            ],
            "temperature": temperature
        }
        if "max_tokens" in kwargs:
             payload["max_tokens"] = kwargs["max_tokens"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/AICodersGuild/ImageClassificationCLI", # Example Referer
            "X-Title": "ImageClassificationCLI" # Example Title
        }

        # console.print(f"[OpenRouterProvider] Sending request to model: {model_id} with temp: {temperature}")
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            # Uvnitř classify_image, po response.raise_for_status()
            # console.print(f"[OpenRouterProvider DEBUG Raw Success Response]: {response.text[:1000]}...") # Logování celé úspěšné odpovědi
            return response.text
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red][OpenRouterProvider] Chyba při volání API: {e}[/bold red]")
            if e.response is not None:
                console.print(f"[bold red][OpenRouterProvider] API Response Status: {e.response.status_code}[/bold red]")
                console.print(f"[bold red][OpenRouterProvider] API Response Text (chyba): {e.response.text[:500]}[/bold red]")
            else:
                console.print(f"[bold red][OpenRouterProvider] Žádná odpověď od API (např. síťová chyba).[/bold red]")
            return None

    def parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        return extract_json_from_text(response_text)
