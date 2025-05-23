import os
import sys
import json
import traceback

from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt, Confirm 
from rich.table import Table 
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.panel import Panel # Added Panel import

from config import (
    INPUT_FOLDER, CATEGORIES_FOLDER, CACHE_FOLDER, OUTPUT_FILE, TAGS_FILE, SETTINGS_FILE,
    MAX_SIZE, MODEL, TEMPERATURE,
    OPENROUTER_API_KEY, OLLAMA_BASE_URL
)
from prompts import PROMPT
    
from providers.base_provider import AbstractAIProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.ollama_provider import OllamaProvider

from image_utils import find_images, resize_image, encode_image
from file_handler import (
    load_tags, save_tags, 
    save_classification_results, organize_file_into_category_folders
)

# --- Globální instance a nastavení ---
custom_theme = Theme({
    "info": "dim cyan", "warning": "magenta", "error": "bold red",
    "success": "green", "prompt": "bold cyan", "path": "underline blue",
    "menu_title": "bold yellow underline", "menu_option": "cyan",
    "menu_key": "bold magenta"
})
console = Console(theme=custom_theme)

app_settings: dict = {}
providers_registry: dict[str, AbstractAIProvider] = {} # Oprava type hintu

# --- Funkce pro načítání a ukládání nastavení ---
def load_app_settings() -> dict:
    global app_settings
    default_settings = {
        "ai_provider_id": "openrouter", "model_id": MODEL, 
        "max_image_size": MAX_SIZE, "recursive_search": True,
        "input_folder": INPUT_FOLDER, "categories_folder": CATEGORIES_FOLDER,
        "cache_folder": CACHE_FOLDER, "output_file": OUTPUT_FILE,
        "tags_file": TAGS_FILE, "temperature": TEMPERATURE,
        "openrouter_api_key": OPENROUTER_API_KEY,
        "ollama_base_url": OLLAMA_BASE_URL,
    }
    loaded_from_file = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded_from_file = json.load(f)
            console.print(f"Nastavení načtena: [path]{SETTINGS_FILE}[/path]", style="info")
        except (json.JSONDecodeError, IOError) as e:
            console.print(f"Chyba načítání [path]{SETTINGS_FILE}[/path]: {e}. Použity výchozí.", style="error")
    else:
        console.print(f"Soubor [path]{SETTINGS_FILE}[/path] nenalezen. Použity výchozí.", style="info")
    
    app_settings = default_settings.copy()
    if loaded_from_file:
        app_settings.update(loaded_from_file)
    
    # Na konci load_app_settings(), před return
    current_provider_id = app_settings.get("ai_provider_id")
    if current_provider_id:
        provider_specific_model_id = app_settings.get(f"{current_provider_id}_model_id")
        if provider_specific_model_id:
            # Ověření, zda tento model stále existuje u providera, by bylo ideální,
            # ale vyžadovalo by to inicializaci providerů a volání load_models() zde,
            # což může být příliš brzy nebo komplikované.
            # Prozatím jednoduše nastavíme, pokud existuje.
            app_settings["model_id"] = provider_specific_model_id
        # Pokud neexistuje specifický model pro providera, ponecháme model_id,
        # které bylo nastaveno z default_settings nebo z hlavního "model_id" v souboru.
        # Případně by se zde mohl nastavit první model od providera, ale to už děláme v on_mount TUI
        # a budeme dělat při výběru providera v CLI nastavení.
    return app_settings

def save_app_settings() -> None:
    global app_settings
    try:
        settings_dir = os.path.dirname(SETTINGS_FILE)
        if settings_dir and not os.path.exists(settings_dir):
            os.makedirs(settings_dir, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(app_settings, f, indent=4, ensure_ascii=False)
        console.print(f"Nastavení uložena: [path]{SETTINGS_FILE}[/path]", style="success")
    except (IOError, OSError) as e:
        console.print(f"Chyba ukládání [path]{SETTINGS_FILE}[/path]: {e}", style="error")

# --- Inicializace providerů ---
def initialize_providers() -> None:
    global providers_registry, app_settings
    providers_registry["openrouter"] = OpenRouterProvider(api_key=app_settings.get("openrouter_api_key"))
    providers_registry["ollama"] = OllamaProvider(base_url=app_settings.get("ollama_base_url"))
    console.print(f"Inicializováno {len(providers_registry)} AI providerů: {', '.join(providers_registry.keys())}", style="info")

# --- Nové funkce menu ---
def zobraz_hlavni_menu() -> None:
    console.print("\n┌" + "─" * 30 + "┐", style="menu_title")
    # Oprava zarovnání titulku, pokud je potřeba - zde ponecháno
    console.print(f"│ [menu_title]Hlavní Menu[/menu_title]                   │")
    console.print("├" + "─" * 30 + "┤", style="menu_title")
    console.print(f"│ [menu_key]1.[/menu_key] [menu_option]Dávkové zpracování[/menu_option]         │")
    console.print(f"│ [menu_key]2.[/menu_key] [menu_option]Interaktivní zpracování[/menu_option]    │")
    console.print(f"│ [menu_key]3.[/menu_key] [menu_option]Nastavení[/menu_option]                  │")
    console.print("├" + "─" * 30 + "┤", style="menu_title")
    console.print(f"│ [menu_key]q.[/menu_key] [menu_option]Konec[/menu_option]                      │")
    console.print("└" + "─" * 30 + "┘", style="menu_title")

# Nová funkce pro dávkové zpracování
def run_batch_processing() -> None:
    global app_settings 
    global providers_registry 
    global console 

    console.print("\n[bold blue]Spouštím dávkové zpracování obrázků...[/bold blue]")

    try:
        input_folder = app_settings.get("input_folder")
        categories_folder = app_settings.get("categories_folder")
        output_file = app_settings.get("output_file")
        tags_file = app_settings.get("tags_file")
        
        ai_provider_id = app_settings.get("ai_provider_id")
        model_id = app_settings.get("model_id")
        temperature = app_settings.get("temperature", 0.2)
        
        provider = providers_registry.get(ai_provider_id)
        if not provider:
            console.print(f"[error]Chyba: Provider '{ai_provider_id}' nenalezen.[/error]")
            return
        if not model_id:
            console.print(f"[error]Chyba: Model ID není nastaveno pro providera '{ai_provider_id}'. Zkontrolujte nastavení.[/error]")
            return

        console.print(f"Použitý provider: [info]{provider.get_provider_name()}[/info], Model: [info]{model_id}[/info]")
        
        existing_tags_set = set(load_tags(tags_file))
        console.print(f"Načteno {len(existing_tags_set)} existujících tagů z [path]{tags_file}[/path].")
        results_aggregator = {}
        
        image_paths = find_images(input_folder) 
        if not image_paths:
            console.print(f"[warning]Nenalezeny žádné obrázky ve složce: [path]{input_folder}[/path].[/warning]")
            return
        
        console.print(f"Nalezeno {len(image_paths)} obrázků ke zpracování.")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            TimeElapsedColumn(),
            console=console, 
            transient=False 
        ) as progress:
            task = progress.add_task("Zpracovávám obrázky...", total=len(image_paths))

            for image_path in image_paths:
                progress.update(task, description=f"Zpracovávám [cyan]{os.path.basename(image_path)}[/cyan]")
                
                try:
                    resized_img_path = resize_image(image_path)
                    
                    b64_image, mime_type = encode_image(resized_img_path)
                    if not b64_image:
                        progress.console.print(f"[warning]Chyba při kódování obrázku {os.path.basename(resized_img_path)}, přeskakuji.[/warning]")
                        progress.advance(task)
                        continue

                    api_response_text = provider.classify_image(
                        model_id=model_id, image_b64=b64_image, mime_type=mime_type,
                        prompt_text=PROMPT, temperature=temperature, existing_tags=list(existing_tags_set)
                    )

                    if not api_response_text:
                        progress.console.print(f"[warning]Žádná odpověď z API pro {os.path.basename(image_path)}, přeskakuji.[/warning]")
                        progress.advance(task)
                        continue

                    extracted_data = provider.parse_json_response(api_response_text)
                    if not extracted_data:
                        progress.console.print(f"[warning]Nepodařilo se extrahovat JSON pro {os.path.basename(image_path)}, přeskakuji.[/warning]")
                        progress.advance(task)
                        continue
                    
                    image_basename = os.path.basename(image_path)
                    current_categories = extracted_data.get("kategorie", [])
                    results_aggregator[image_basename] = {
                        "kategorie": current_categories, "popis": extracted_data.get("popis", ""),
                        "tagy": extracted_data.get("tagy", {}), "text": extracted_data.get("text", "")
                    }

                    if "tagy" in extracted_data and isinstance(extracted_data["tagy"], dict):
                        tag_groups = extracted_data["tagy"]
                        for category_tags_list in tag_groups.values():
                            if isinstance(category_tags_list, list):
                                for tag_val in category_tags_list:
                                    if isinstance(tag_val, str) and tag_val:
                                        processed_tag = tag_val.lower()
                                        existing_tags_set.add(processed_tag)
                        
                    if current_categories:
                        organize_file_into_category_folders(
                            image_path, current_categories, categories_folder, image_basename
                        )
                except Exception as e_img:
                    progress.console.print(f"[error]Chyba při zpracování obrázku {os.path.basename(image_path)}: {e_img}[/error]")
                
                progress.advance(task)
        
        save_classification_results(output_file, results_aggregator)
        save_tags(tags_file, sorted(list(existing_tags_set)))
        console.print(f"\n[success]Dávkové zpracování dokončeno! Výsledky uloženy do [path]{output_file}[/path] a tagy do [path]{tags_file}[/path].[/success]")

    except Exception as e_batch:
        console.print(f"[error]Neočekávaná chyba během dávkového zpracování: {e_batch}[/error]")
        console.print_exception(show_locals=True) 

def spusti_davkovy_mod() -> None:
    console.rule("[bold cyan]Dávkové Zpracování[/bold cyan]", style="cyan")
    if Confirm.ask("[prompt]Opravdu chcete spustit dávkové zpracování s aktuálním nastavením?[/prompt]", default=False):
        run_batch_processing()
    else:
        console.print("[info]Dávkové zpracování zrušeno uživatelem.[/info]")
    Prompt.ask("\nStiskněte Enter pro návrat do menu...", default="", show_default=False)

# Nová funkce pro interaktivní zpracování
def run_interactive_processing() -> None:
    global app_settings, providers_registry, console

    console.rule("[bold magenta]Interaktivní Zpracování[/bold magenta]", style="magenta")

    try:
        input_folder = app_settings.get("input_folder")
        categories_folder = app_settings.get("categories_folder")
        output_file = app_settings.get("output_file") 
        tags_file = app_settings.get("tags_file")     

        ai_provider_id = app_settings.get("ai_provider_id")
        model_id = app_settings.get("model_id")
        temperature = app_settings.get("temperature", 0.2)

        provider = providers_registry.get(ai_provider_id)
        if not provider:
            console.print(f"[error]Chyba: Provider '{ai_provider_id}' nenalezen.[/error]")
            return
        if not model_id:
            console.print(f"[error]Chyba: Model ID není nastaveno pro providera '{ai_provider_id}'. Zkontrolujte nastavení.[/error]")
            return

        console.print(f"Použitý provider: [info]{provider.get_provider_name()}[/info], Model: [info]{model_id}[/info]")

        image_paths = find_images(input_folder)
        if not image_paths:
            console.print(f"[warning]Nenalezeny žádné obrázky ve složce: [path]{input_folder}[/path].[/warning]")
            return

        interactive_results_aggregator = {}
        
        current_image_index = 0
        while current_image_index < len(image_paths):
            image_path = image_paths[current_image_index]
            image_basename = os.path.basename(image_path)
            
            console.rule(f"[bold]Obrázek ({current_image_index + 1}/{len(image_paths)}): {image_basename}[/bold]", style="blue")
            
            extracted_data = None
            try:
                resized_img_path = resize_image(image_path)
                b64_image, mime_type = encode_image(resized_img_path)

                if not b64_image:
                    console.print(f"[warning]Chyba při kódování obrázku, přeskakuji.[/warning]")
                    current_image_index += 1
                    continue

                current_tags_for_prompt = set(load_tags(tags_file))

                api_response_text = provider.classify_image(
                    model_id=model_id, image_b64=b64_image, mime_type=mime_type,
                    prompt_text=PROMPT, temperature=temperature, existing_tags=list(current_tags_for_prompt)
                )

                if not api_response_text:
                    console.print(f"[warning]Žádná odpověď z API, přeskakuji.[/warning]")
                    current_image_index += 1
                    continue
                
                extracted_data = provider.parse_json_response(api_response_text)
                if not extracted_data:
                    console.print(f"[warning]Nepodařilo se extrahovat JSON, přeskakuji.[/warning]")
                    current_image_index += 1
                    continue
                
                console.print(Panel.fit(
                    f"[bold]Kategorie:[/bold] {', '.join(extracted_data.get('kategorie', ['N/A']))}\n"
                    f"[bold]Popis:[/bold] {extracted_data.get('popis', 'N/A')}\n"
                    f"[bold]Tagy:[/bold] {json.dumps(extracted_data.get('tagy', {}), ensure_ascii=False, indent=2)}\n"
                    f"[bold]Extrahovaný text:[/bold] {extracted_data.get('text', 'N/A')}",
                    title="Výsledky Klasifikace"
                ))

            except Exception as e_img:
                console.print(f"[error]Chyba při zpracování obrázku {image_basename}: {e_img}[/error]")
                if not Confirm.ask("[prompt]Pokračovat na další obrázek i přes chybu?[/prompt]", default=True):
                    break 
                current_image_index += 1
                continue
            
            console.print("\n[bold]Akce:[/bold]")
            akce = Prompt.ask(
                "[prompt]([menu_key]s[/menu_key])chválit a další, ([menu_key]p[/menu_key])řeskočit, ([menu_key]u[/menu_key])pravit (TODO), ([menu_key]q[/menu_key])končit interaktivní režim[/prompt]",
                choices=["s", "p", "u", "q"],
                default="s"
            ).lower()

            if akce == 's':
                if extracted_data: 
                    interactive_results_aggregator[image_basename] = extracted_data
                    console.print(f"[success]Obrázek '{image_basename}' schválen.[/success]")
                    current_categories = extracted_data.get("kategorie", [])
                    if current_categories:
                        organize_file_into_category_folders(
                            image_path, current_categories, categories_folder, image_basename
                        )
                else:
                    console.print(f"[warning]Žádná data k uložení pro '{image_basename}'.[/warning]")
            elif akce == 'p':
                console.print(f"[info]Obrázek '{image_basename}' přeskočen.[/info]")
            elif akce == 'u':
                console.print("[warning]Funkce 'Upravit' zatím není implementována.[/warning]")
                current_image_index -=1 
            elif akce == 'q':
                console.print("[info]Interaktivní režim ukončen uživatelem.[/info]")
                break 
            
            current_image_index += 1
        
        if not interactive_results_aggregator:
            console.print("\n[info]Nebyly schváleny žádné obrázky k uložení v této session.[/info]")
        else:
            console.print(f"\n[info]Ukládám {len(interactive_results_aggregator)} schválených výsledků...[/info]")
            save_classification_results(output_file, interactive_results_aggregator)
            
            console.print(f"[info]Aktualizuji globální tagy...[/info]")
            existing_tags_set = set(load_tags(tags_file))
            for item_data in interactive_results_aggregator.values():
                if "tagy" in item_data and isinstance(item_data["tagy"], dict):
                    tag_groups = item_data["tagy"]
                    for category_tags_list in tag_groups.values():
                        if isinstance(category_tags_list, list):
                            for tag_val in category_tags_list:
                                if isinstance(tag_val, str) and tag_val:
                                    existing_tags_set.add(tag_val.lower())
            save_tags(tags_file, sorted(list(existing_tags_set)))
            console.print(f"[success]Výsledky a tagy uloženy.[/success]")

    except Exception as e_interactive:
        console.print(f"[error]Neočekávaná chyba v interaktivním režimu: {e_interactive}[/error]")
        console.print_exception(show_locals=True)
    
    console.print("[info]Interaktivní zpracování dokončeno.[/info]")

def spusti_interaktivni_mod() -> None:
    if Confirm.ask("[prompt]Opravdu chcete spustit interaktivní zpracování s aktuálním nastavením?[/prompt]", default=True):
        run_interactive_processing()
    else:
        console.print("[info]Interaktivní zpracování zrušeno uživatelem.[/info]")
    Prompt.ask("\nStiskněte Enter pro návrat do menu...", default="", show_default=False)

# Toto je nový obsah pro funkci spravuj_nastaveni()
def spravuj_nastaveni() -> None:
    global app_settings
    global providers_registry

    while True:
        console.print("\n┌" + "─" * 45 + "┐", style="menu_title")
        console.print(f"│ [menu_title]Menu Nastavení[/menu_title]                               │")
        console.print("├" + "─" * 45 + "┤", style="menu_title")
        
        # Uvnitř while True v spravuj_nastaveni(), při sestavování zobrazení menu
        current_provider_id = app_settings.get('ai_provider_id', 'N/A')
        # Nejprve zkusíme model specifický pro providera
        model_to_display_id = app_settings.get(f"{current_provider_id}_model_id")
        if not model_to_display_id: # Pokud není, vezmeme obecný model_id
            model_to_display_id = app_settings.get('model_id', 'N/A')
        
        model_display_name = model_to_display_id
        if current_provider_id != 'N/A' and providers_registry.get(current_provider_id) and model_to_display_id != 'N/A':
            try:
                models_for_provider = providers_registry[current_provider_id].load_models()
                for m in models_for_provider:
                    if m.get('id') == model_to_display_id:
                        model_display_name = f"{m.get('name')} ({m.get('id')})"
                        break
            except Exception: pass # Zobrazí se jen ID, pokud se nepodaří načíst jméno
        
        console.print(f"│ [menu_key]1.[/menu_key] [menu_option]AI Provider[/menu_option]: [info]{current_provider_id}[/info]")
        console.print(f"│ [menu_key]2.[/menu_key] [menu_option]Model[/menu_option]: [info]{model_display_name}[/info]")
        console.print(f"│ [menu_key]3.[/menu_key] [menu_option]Max. velikost obr. (px)[/menu_option]: [info]{app_settings.get('max_image_size', 'N/A')}[/info]")
        console.print(f"│ [menu_key]4.[/menu_key] [menu_option]Rekurzivní hledání[/menu_option]: [info]{'Ano' if app_settings.get('recursive_search') else 'Ne'}[/info]")
        console.print(f"│ [menu_key]5.[/menu_key] [menu_option]Zdrojová složka[/menu_option]: [path]{app_settings.get('input_folder', 'N/A')}[/path]")
        console.print(f"│ [menu_key]6.[/menu_key] [menu_option]Výstupní složka (kategorie)[/menu_option]: [path]{app_settings.get('categories_folder', 'N/A')}[/path]")
        console.print(f"│ [menu_key]7.[/menu_key] [menu_option]Složka pro cache[/menu_option]: [path]{app_settings.get('cache_folder', 'N/A')}[/path]")
        console.print(f"│ [menu_key]8.[/menu_key] [menu_option]Teplota (AI model)[/menu_option]: [info]{app_settings.get('temperature', 'N/A')}[/info]")
        console.print("├" + "─" * 45 + "┤", style="menu_title")
        console.print(f"│ [menu_key]q.[/menu_key] [menu_option]Zpět do hlavního menu[/menu_option]                      │")
        console.print("└" + "─" * 45 + "┘", style="menu_title")

        volba = Prompt.ask(
            "[prompt]Zadejte číslo položky pro změnu nebo 'q' pro návrat[/prompt]",
            choices=['1', '2', '3', '4', '5', '6', '7', '8', 'q'],
            default='q',
            show_default=False
        ).lower()

        if volba == 'q':
            save_app_settings()
            break
        
        try:
            if volba == '1':
                provider_ids = list(providers_registry.keys())
                if not provider_ids:
                    console.print("[error]Nejsou dostupní žádní AI provideři.[/error]")
                    continue
                table = Table(title="Dostupní AI Provideři")
                table.add_column("Klíč", style="menu_key", justify="right")
                table.add_column("Název Providera", style="menu_option")
                for i, pid in enumerate(provider_ids): table.add_row(str(i + 1), providers_registry[pid].get_provider_name())
                console.print(table)
                provider_choice = Prompt.ask("[prompt]Vyberte číslo providera[/prompt]", choices=[str(i + 1) for i in range(len(provider_ids))], show_default=False)
                selected_provider_id = provider_ids[int(provider_choice) - 1]
                app_settings['ai_provider_id'] = selected_provider_id
                
                # Uvnitř if volba == '1', po nastavení app_settings['ai_provider_id']
                # Pokusíme se načíst dříve uložený model pro tohoto nově vybraného providera
                provider_specific_model_id = app_settings.get(f"{selected_provider_id}_model_id")
                
                new_active_model_id = None
                try:
                    models = providers_registry[selected_provider_id].load_models()
                    if models:
                        if provider_specific_model_id and any(m['id'] == provider_specific_model_id for m in models):
                            new_active_model_id = provider_specific_model_id
                        else: # Pokud specifický model není nebo už neexistuje, vezmi první dostupný
                            new_active_model_id = models[0]['id']
                    app_settings['model_id'] = new_active_model_id # Nastaví nový aktivní model (nebo None)
                    # Není potřeba zde explicitně ukládat do app_settings[f"{selected_provider_id}_model_id"],
                    # protože to se děje až při výběru modelu (volba '2').
                    # Ale pokud chceme, aby se první model stal "zapamatovaným" pro providera hned:
                    if new_active_model_id:
                         app_settings[f"{selected_provider_id}_model_id"] = new_active_model_id

                except Exception as e:
                    console.print(f"[error]Nepodařilo se načíst modely pro {selected_provider_id}: {e}[/error]")
                    app_settings['model_id'] = None # Reset aktivního modelu
                
                console.print(f"AI Provider nastaven na: [success]{selected_provider_id}[/success]")
                if app_settings.get('model_id'):
                    console.print(f"Aktivní model pro '{selected_provider_id}' automaticky nastaven na: [info]{app_settings.get('model_id')}[/info]")
                else:
                    console.print(f"[warning]Pro providera '{selected_provider_id}' nebyl automaticky nastaven žádný model. Vyberte prosím model ručně (volba 2).[/warning]")
            
            elif volba == '2':
                current_provider_id = app_settings.get('ai_provider_id')
                if not current_provider_id or not providers_registry.get(current_provider_id):
                    console.print("[error]Nejprve vyberte platného AI Providera (volba 1).[/error]")
                    continue
                provider = providers_registry[current_provider_id]
                models = provider.load_models()
                if not models:
                    console.print(f"[warning]Pro providera '{provider.get_provider_name()}' nebyly nalezeny žádné modely.[/warning]")
                    continue
                
                # Uvnitř if volba == '2', při vytváření Table
                table = Table(title=f"Dostupné modely pro {provider.get_provider_name()}")
                table.add_column("Klíč", style="menu_key", justify="right")
                table.add_column("Název Modelu (ID)", style="menu_option", max_width=50) # Omezení šířky
                table.add_column("Free", style="dim", width=6)
                table.add_column("Context", style="dim", width=10)
                table.add_column("Popis", style="dim", overflow="fold") # Zalamování popisu
                
                for i, model_data in enumerate(models):
                    is_free = "Ano" if model_data.get('free') else "Ne"
                    context = str(model_data.get('context_window', 'N/A'))
                    table.add_row(
                        str(i + 1), 
                        f"{model_data['name']} \n([dim]{model_data['id']}[/dim])", # ID menším písmem
                        is_free,
                        context,
                        model_data.get('description', '')
                    )
                console.print(table)
                model_choice = Prompt.ask("[prompt]Vyberte číslo modelu[/prompt]", choices=[str(i + 1) for i in range(len(models))], show_default=False)
                selected_model_id = models[int(model_choice) - 1]['id']
                app_settings['model_id'] = selected_model_id
                app_settings[f"{current_provider_id}_model_id"] = selected_model_id
                console.print(f"Model nastaven na: [success]{selected_model_id}[/success]")
            elif volba == '3':
                new_val_str = Prompt.ask(f"[prompt]Nová max. velikost (aktuální: {app_settings.get('max_image_size')})[/prompt]", default=str(app_settings.get('max_image_size')))
                try:
                    new_val = int(new_val_str)
                    if new_val > 0: app_settings['max_image_size'] = new_val; console.print(f"Max. velikost nastavena: [success]{new_val}px[/success]")
                    else: console.print("[error]Velikost musí být kladné číslo.[/error]")
                except ValueError: console.print("[error]Neplatný formát čísla.[/error]")
            elif volba == '4':
                current_val = app_settings.get('recursive_search', True)
                app_settings['recursive_search'] = Confirm.ask(f"[prompt]Rekurzivní hledání (aktuální: {'Ano' if current_val else 'Ne'})[/prompt]", default=current_val)
                console.print(f"Rekurzivní hledání: [success]{'Ano' if app_settings['recursive_search'] else 'Ne'}[/success]")
            elif volba == '5':
                new_val = Prompt.ask(f"[prompt]Nová zdrojová složka (aktuální: {app_settings.get('input_folder')})[/prompt]", default=app_settings.get('input_folder')).strip()
                if new_val: app_settings['input_folder'] = new_val; console.print(f"Zdrojová složka: [path]{new_val}[/path]")
                else: console.print("[warning]Cesta nesmí být prázdná.[/warning]")
            elif volba == '6':
                new_val = Prompt.ask(f"[prompt]Nová výstupní složka (aktuální: {app_settings.get('categories_folder')})[/prompt]", default=app_settings.get('categories_folder')).strip()
                if new_val: app_settings['categories_folder'] = new_val; console.print(f"Výstupní složka: [path]{new_val}[/path]")
                else: console.print("[warning]Cesta nesmí být prázdná.[/warning]")
            elif volba == '7':
                new_val = Prompt.ask(f"[prompt]Nová složka pro cache (aktuální: {app_settings.get('cache_folder')})[/prompt]", default=app_settings.get('cache_folder')).strip()
                if new_val: app_settings['cache_folder'] = new_val; console.print(f"Složka pro cache: [path]{new_val}[/path]")
                else: console.print("[warning]Cesta nesmí být prázdná.[/warning]")
            elif volba == '8':
                new_val_str = Prompt.ask(f"[prompt]Nová teplota (0.0-2.0, aktuální: {app_settings.get('temperature')})[/prompt]", default=str(app_settings.get('temperature')))
                try:
                    new_val = float(new_val_str)
                    if 0.0 <= new_val <= 2.0: app_settings['temperature'] = new_val; console.print(f"Teplota nastavena: [success]{new_val}[/success]")
                    else: console.print("[error]Teplota musí být mezi 0.0 a 2.0.[/error]")
                except ValueError: console.print("[error]Neplatný formát čísla.[/error]")
        except Exception as e:
            console.print(f"[bold red]Nastala chyba v menu nastavení: {e}[/bold red]")

# --- Hlavní CLI funkce (s menu smyčkou) ---
def cli() -> None:
    global app_settings
    app_settings = load_app_settings()
    initialize_providers()
    
    console.print("[bold green]Vítejte v AiZr Image Classifier CLI![/bold green]")
    
    while True:
        zobraz_hlavni_menu()
        # Použijeme choices pro validaci vstupu přímo v Prompt.ask
        volba = Prompt.ask(
            "[prompt]Zadejte vaši volbu[/prompt]", 
            choices=['1', '2', '3', 'q'], 
            default='q', 
            show_default=False
        ).lower()

        if volba == '1':
            spusti_davkovy_mod()
        elif volba == '2':
            spusti_interaktivni_mod()
        elif volba == '3':
            spravuj_nastaveni()
        elif volba == 'q':
            console.print("[bold green]Ukončuji aplikaci. Na shledanou![/bold green]")
            save_app_settings() # Uložíme nastavení při korektním ukončení
            break
        # else: # Díky choices v Prompt.ask by se sem kód neměl dostat
        #     console.print("[error]Neplatná volba, zkuste to znovu.[/error]")

if __name__ == "__main__":
    cli()
```
