import requests
import json
import re
from config import console # API_KEY, MODEL, TEMPERATURE are now passed as arguments
# PROMPT is now passed as prompt_template argument

# Updated function signature
def classify_image(api_key, model, temp, image_b64, mime_type, prompt_template, existing_tags: list[str] = None):
    """
    Classifies an image using an external API.
    (This is a placeholder and would need a real API endpoint and payload structure)
    """
    # console.print(f"[API Client] Classifying image via API. Mime-type: {mime_type}") # image_path no longer available for logging here
    
    current_prompt = prompt_template
    if existing_tags: # Check if list is not empty or None
        tags_text = ", ".join(existing_tags)
        tags_section_text = f"- Zde je seznam existujících tagů, které bys měl/a preferovat, pokud se hodí: [{tags_text}].\n"
        current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", tags_section_text)
    else:
        current_prompt = current_prompt.replace("{{EXISTING_TAGS_SECTION}}\n", "")

    # The new PROMPT from prompts.py no longer uses .format(categories=...)
    # The categories are listed directly in the prompt.
    # If specific runtime categories were still needed, the prompt_template would need a {categories} placeholder.
    # For now, assuming current_prompt is ready.

    # This is a placeholder for the actual API call structure.
    # The prompt asks for a JSON response, so the API should be called accordingly.
    # The example here is for an OpenRouter-like API with messages structure.
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": current_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": temp,
        # "max_tokens": MAX_SIZE, # MAX_SIZE is not passed, if needed, add to signature
        # "response_format": {"type": "json_object"} # If API supports JSON mode
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    console.print(f"[API Client] Sending request to model: {model} with temp: {temp}")
    # console.print(f"[API Client] Payload messages (text part): {current_prompt[:200]}...") # For brevity

    try:
        # Actual API call would be something like:
        # response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
        # response.raise_for_status()
        # api_response_text = response.text # Or response.json() if API returns JSON object directly

        # Placeholder response for testing the structure:
        # This should now be a JSON string as per the updated PROMPT's request.
        api_response_text = json.dumps({
            "kategorie": ["placeholder_kategorie"],
            "popis": "Placeholder popis obrázku.",
            "tagy": {
                "scena": ["placeholder_scena"],
                "prostredi": ["placeholder_prostredi"],
                "objekty_aktivity": ["placeholder_objekt"],
                "libovolne": ["placeholder_tag"]
            },
            "text": "Placeholder extrahovaný text."
        })
        
        console.print(f"[API Client] Simulated API Response: {api_response_text}")
        return api_response_text 
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red][API Client] Error during API call: {e}[/bold red]")
        return None

def extract_json(text: str) -> dict | None:
    if not text:
        console.print("[yellow]extract_json: Prázdný vstupní text.[/yellow]")
        return None

    # Pokus najít JSON blok, který může být obalen ```json ... ```
    # Používáme re.IGNORECASE pro větší flexibilitu s ```JSON, ```json, atd.
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if not match:
        # Pokud není nalezen s ```json, zkus najít obecný JSON objekt.
        # Tento obecnější regex by měl být aplikován jako druhý, aby se předešlo chybnému zachycení,
        # pokud je přítomen specifičtější ```json ... ``` formát.
        match = re.search(r"(\{.*\})", text, re.DOTALL)

    if match:
        json_str = match.group(1) # group(1) protože chceme obsah závorek {}
        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                console.print(f"[red]extract_json: Naparsovaná data nejsou slovník: {type(data)}[/red]")
                return None
            # Validace klíče "kategorie"
            if "kategorie" not in data or not isinstance(data.get("kategorie"), list):
                console.print("[red]extract_json: JSON neobsahuje klíč 'kategorie' s listem hodnot.[/red]")
                # Podle zadání jsou kategorie klíčové, takže vracíme None.
                return None
            # Můžeme přidat další validace podle potřeby, např. pro 'popis', 'tagy', 'text'
            # if "popis" not in data or not isinstance(data.get("popis"), str):
            #     console.print("[red]extract_json: JSON neobsahuje klíč 'popis' s textovou hodnotou.[/red]")
            #     return None
            # if "tagy" not in data or not isinstance(data.get("tagy"), dict):
            #     console.print("[red]extract_json: JSON neobsahuje klíč 'tagy' se slovníkem hodnot.[/red]")
            #     return None
            # if "text" not in data or not isinstance(data.get("text"), str):
            #     console.print("[red]extract_json: JSON neobsahuje klíč 'text' s textovou hodnotou.[/red]")
            #     return None
            return data
        except json.JSONDecodeError as e:
            # Vypíšeme pouze část problematického stringu, abychom nezahltili log.
            error_snippet = json_str[:500] + "..." if len(json_str) > 500 else json_str
            console.print(f"[red]extract_json: Chyba při parsování JSON: {e}[/red]")
            console.print(f"[red]extract_json: Problematický JSON string (začátek): {error_snippet}[/red]")
            return None
    else:
        # Vypíšeme pouze část celé odpovědi pro kontext.
        response_snippet = text[:500] + "..." if len(text) > 500 else text
        console.print("[yellow]extract_json: JSON blok nenalezen v odpovědi API.[/yellow]")
        console.print(f"[yellow]extract_json: Celá odpověď (začátek): {response_snippet}[/yellow]")
        return None
