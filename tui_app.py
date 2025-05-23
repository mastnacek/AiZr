import os
import sys
import traceback
import json 
from typing import List, Dict, Any, Optional 
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, RichLog

# Importy pro Screens a konfiguraci
from screens.settings_screen import SettingsScreen
from screens.interactive_screen import (
    InteractiveProcessingScreen, 
    ApproveMessage, 
    SkipMessage, 
    EndInteractiveMessage
)
from config import (
    INPUT_FOLDER, CATEGORIES_FOLDER, CACHE_FOLDER, OUTPUT_FILE, TAGS_FILE, SETTINGS_FILE,
    MAX_SIZE, MODEL, TEMPERATURE, OPENROUTER_API_KEY, OLLAMA_BASE_URL, 
    console as global_config_console 
)
# Importy providerů
from providers.openrouter_provider import OpenRouterProvider
from providers.ollama_provider import OllamaProvider

# Importy pro logiku zpracování
from prompts import PROMPT
from image_utils import (
    resize_image,
    find_images, 
    encode_image
)
from file_handler import (
    load_tags, 
    save_tags, 
    save_classification_results,
    organize_file_into_category_folders
)

# --- Processing Screen Definition ---
class ProcessingScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header(name="Zpracování obrázků...")
        yield RichLog(id="process_log", wrap=True, highlight=True, markup=True)
        yield Footer()
    
    def on_mount(self) -> None:
        pass # Logging is handled by _log_to_screen in the App

# --- Main Application CSS ---
APP_CSS = """
Screen {
    align: center middle;
}
#main-menu-container {
    width: auto;
    padding: 1;
}
.menu-title {
    padding-bottom: 1;
}
Button {
    width: 100%;
    margin-top: 1;
}
ProcessingScreen RichLog {
    border: round $primary;
    width: 100%;
    height: 80%; 
    margin: 1 0;
}
"""

class MainScreen(Screen):
    BINDINGS = [
        ("q", "request_quit", "Konec"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(name="Image Classifier TUI")
        with Vertical(id="main-menu-container"):
            yield Static("Hlavní menu:", classes="menu-title")
            yield Button("Dávkové zpracování", id="batch_processing", variant="primary")
            yield Button("Interaktivní zpracování", id="interactive_processing", variant="success")
            yield Button("Nastavení", id="settings")
            yield Button("Konec", id="quit_app", variant="error")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit_app":
            self.app.exit("Ukončeno uživatelem z hlavního menu.")
        elif event.button.id == "settings":
            self.app.push_screen("settings") 
        elif event.button.id == "batch_processing":
            await self.app.action_trigger_processing() 
        elif event.button.id == "interactive_processing":
            await self.app.action_start_interactive_processing()

    def action_request_quit(self) -> None:
        self.app.exit("Ukončeno uživatelem (klávesa 'q').")

class ImageClassifierApp(App[None]):
    TITLE = "Image Classifier TUI"
    CSS = APP_CSS 
    
    SCREENS = {
        "settings": SettingsScreen,
        "processing": ProcessingScreen,
        "interactive": InteractiveProcessingScreen 
    }
    
    interactive_image_paths: List[str] = []
    current_interactive_index: int = -1
    interactive_results_aggregator: Dict[str, Any] = {}

    def on_mount(self) -> None:
        loaded_settings = {}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                self.notify("Nastavení úspěšně načtena ze souboru.", title="Info")
            else:
                self.notify("Soubor s nastavením nenalezen, použijí se výchozí hodnoty.", title="Info")
        except (json.JSONDecodeError, IOError) as e:
            self.notify(f"Chyba načítání nastavení: {e}. Použijí se výchozí hodnoty.", title="Chyba", severity="error")
            loaded_settings = {}

        program_defaults = {
            "ai_provider_id": "openrouter", "model_id": MODEL, "max_image_size": MAX_SIZE,
            "recursive_search": True, "input_folder": INPUT_FOLDER, "categories_folder": CATEGORIES_FOLDER,
            "cache_folder": CACHE_FOLDER, "temperature": TEMPERATURE, "output_file": OUTPUT_FILE,
            "tags_file": TAGS_FILE,
        }
        self.app_settings = program_defaults.copy()
        for key, value in loaded_settings.items():
            if key in self.app_settings:
                if key == "max_image_size" and isinstance(value, (str, int)):
                    try: self.app_settings[key] = int(value)
                    except ValueError: pass 
                elif key == "recursive_search" and isinstance(value, bool):
                    self.app_settings[key] = value
                elif key == "temperature" and isinstance(value, (float, int)):
                    try: self.app_settings[key] = float(value)
                    except ValueError: pass
                elif key in ["ai_provider_id", "model_id", "input_folder", "categories_folder", "cache_folder", "output_file", "tags_file"]:
                    if isinstance(value, str) or value is None: 
                        self.app_settings[key] = value
                elif key.endswith("_model_id") and isinstance(value, str):
                     self.app_settings[key] = value

        self.providers_registry = {
            "openrouter": OpenRouterProvider(), "ollama": OllamaProvider(),
        }
        
        current_ai_provider_id = self.app_settings.get("ai_provider_id", "openrouter")
        current_model_id = self.app_settings.get(f"{current_ai_provider_id}_model_id")
        
        if not current_model_id: 
            if current_ai_provider_id in self.providers_registry:
                try:
                    current_provider_models = self.providers_registry[current_ai_provider_id].load_models()
                    if current_provider_models:
                        current_model_id = current_provider_models[0]['id']
                except Exception as e:
                    self.console.print(f"Chyba při načítání modelů pro {current_ai_provider_id} v on_mount: {e}")
        if not current_model_id:
            current_model_id = MODEL 
        self.app_settings["model_id"] = current_model_id
        self.app_settings["ai_provider_id"] = current_ai_provider_id
        self.push_screen(MainScreen())

    def update_app_settings(self, new_settings: dict) -> None:
        if "ai_provider" in new_settings and "ai_provider_id" not in new_settings:
            new_settings["ai_provider_id"] = new_settings.pop("ai_provider")
        self.app_settings.update(new_settings)
        current_provider_id = self.app_settings.get("ai_provider_id")
        current_model_id = self.app_settings.get("model_id")
        if current_provider_id and current_model_id:
            self.app_settings[f"{current_provider_id}_model_id"] = current_model_id
        self.notify("Globální nastavení aplikace aktualizována.", title="Nastavení")
        try:
            settings_dir = os.path.dirname(SETTINGS_FILE)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.app_settings, f, indent=4, ensure_ascii=False)
        except (IOError, OSError) as e: 
            self.notify(f"Chyba ukládání nastavení: {e}", title="Chyba", severity="error")

    def _log_to_screen(self, message: str) -> None:
        try:
            if isinstance(self.screen, ProcessingScreen) or isinstance(self.screen, InteractiveProcessingScreen):
                log_widget = self.screen.query_one("#process_log", RichLog) # Assuming InteractiveScreen also has #process_log
                log_widget.write(message)
            else:
                self.console.print(message)
        except Exception: # Fallback if query_one fails or other issues
            global_config_console.print(message)


    def _execute_image_processing_logic(self) -> None: 
        log_widget = None
        if isinstance(self.screen, ProcessingScreen): # Batch processing screen
            log_widget = self.screen.query_one("#process_log", RichLog)
        def log_message(message: str): # Use App's _log_to_screen for broader compatibility
            self.call_from_thread(self._log_to_screen, message)

        try:
            log_message("[bold blue]Spouštím proces klasifikace obrázků...[/bold blue]")
            input_folder = self.app_settings.get("input_folder", INPUT_FOLDER)
            categories_folder = self.app_settings.get("categories_folder", CATEGORIES_FOLDER)
            output_file = self.app_settings.get("output_file", OUTPUT_FILE)
            tags_file = self.app_settings.get("tags_file", TAGS_FILE)
            ai_provider_id = self.app_settings.get("ai_provider_id")
            model_id = self.app_settings.get("model_id")
            temperature = self.app_settings.get("temperature", TEMPERATURE)
            provider = self.providers_registry.get(ai_provider_id)
            if not provider:
                log_message(f"[bold red]Chyba: Provider '{ai_provider_id}' nenalezen.[/bold red]")
                return
            log_message(f"[bold blue]Provider: {provider.get_provider_name()}, Model: {model_id}[/bold blue]")
            existing_tags_list = load_tags(tags_file)
            existing_tags_set = set(existing_tags_list)
            log_message(f"Načteno {len(existing_tags_set)} existujících tagů z {tags_file}.")
            results_aggregator = {}
            image_paths = find_images(input_folder)
            if not image_paths:
                log_message(f"[yellow]Nenalezeny žádné obrázky ve složce: {input_folder}.[/yellow]")
                return
            log_message(f"Nalezeno {len(image_paths)} obrázků ke zpracování.")
            for i, image_path in enumerate(image_paths):
                log_message(f"\n[cyan]Zpracovávám ({i+1}/{len(image_paths)}): {os.path.basename(image_path)}[/cyan]")
                resized_img_path = resize_image(image_path)
                log_message(f"Použitá verze obrázku pro API: {os.path.basename(resized_img_path)}")
                b64_image, mime_type = encode_image(resized_img_path)
                if not b64_image:
                    log_message(f"[yellow]Chyba při kódování obrázku {os.path.basename(resized_img_path)}, přeskakuji.[/yellow]")
                    continue
                api_response_text = provider.classify_image(
                    model_id=model_id, image_b64=b64_image, mime_type=mime_type,
                    prompt_text=PROMPT, temperature=temperature, existing_tags=list(existing_tags_set)
                )
                if not api_response_text:
                    log_message(f"[yellow]Žádná odpověď z API pro {os.path.basename(image_path)}, přeskakuji.[/yellow]")
                    continue
                extracted_data = provider.parse_json_response(api_response_text)
                if not extracted_data:
                    log_message(f"[yellow]Nepodařilo se extrahovat JSON pro {os.path.basename(image_path)}, přeskakuji.[/yellow]")
                    continue
                image_basename = os.path.basename(image_path)
                current_categories = extracted_data.get("kategorie", [])
                results_aggregator[image_basename] = {
                    "kategorie": current_categories, "popis": extracted_data.get("popis", ""),
                    "tagy": extracted_data.get("tagy", {}), "text": extracted_data.get("text", "")
                }
                if "tagy" in extracted_data and isinstance(extracted_data["tagy"], dict):
                    tag_groups = extracted_data["tagy"]
                    newly_added_count = 0
                    for category_tags_list in tag_groups.values():
                        if isinstance(category_tags_list, list):
                            for tag_val in category_tags_list:
                                if isinstance(tag_val, str) and tag_val:
                                    processed_tag = tag_val.lower()
                                    if processed_tag not in existing_tags_set:
                                        newly_added_count +=1
                                    existing_tags_set.add(processed_tag)
                    if newly_added_count > 0:
                            log_message(f"Přidáno {newly_added_count} nových unikátních tagů.")
                if current_categories:
                    organize_file_into_category_folders(
                        image_path, current_categories, categories_folder, image_basename
                    )
            save_classification_results(output_file, results_aggregator)
            save_tags(tags_file, sorted(list(existing_tags_set)))
            log_message(f"\n[bold green]Zpracování dokončeno! Výsledky uloženy do {output_file} a tagy do {tags_file}.[/bold green]")
        except Exception as e:
            log_message(f"[bold red]Neočekávaná chyba během zpracování: {e}[/bold red]")
            log_message(f"[bold red]Traceback: {traceback.format_exc()}[/bold red]")

    async def action_trigger_processing(self) -> None: # Batch processing
        await self.push_screen("processing")
        self.run_worker(self._execute_image_processing_logic, thread=True)

    # --- Metody pro interaktivní režim ---
    async def _load_next_interactive_image(self) -> None:
        self.current_interactive_index += 1
        if self.current_interactive_index < len(self.interactive_image_paths):
            current_image_path = self.interactive_image_paths[self.current_interactive_index]
            self._log_to_screen(f"Načítám pro interaktivní režim: {current_image_path}")
            ai_provider_id = self.app_settings.get("ai_provider_id")
            model_id = self.app_settings.get("model_id")
            temperature = self.app_settings.get("temperature", 0.2)
            provider = self.providers_registry.get(ai_provider_id)
            if not provider:
                self.notify(f"Chyba: Provider '{ai_provider_id}' nenalezen.", severity="error", title="Chyba Providera")
                await self._handle_interactive_error_or_end()
                return
            try:
                # TODO: Spustit toto v self.run_worker
                resized_path = resize_image(current_image_path)
                b64_img, mime = encode_image(resized_path)
                if not b64_img:
                    self.notify(f"Chyba kódování obrázku: {os.path.basename(current_image_path)}", severity="error", title="Chyba Obrázku")
                    await self._load_next_interactive_image()
                    return
                current_existing_tags = list(load_tags(self.app_settings.get("tags_file", TAGS_FILE)))
                api_response = provider.classify_image(
                    model_id=model_id, image_b64=b64_img, mime_type=mime,
                    prompt_text=PROMPT, temperature=temperature,
                    existing_tags=current_existing_tags
                )
                extracted_data = None
                if api_response: extracted_data = provider.parse_json_response(api_response)
                if not extracted_data:
                    self.notify(f"Chyba klasifikace/parsování: {os.path.basename(current_image_path)}", severity="warning", title="Chyba Klasifikace")
                    extracted_data = {}
                
                # Zajištění, že jsme na správné obrazovce nebo přepnutí
                if not isinstance(self.screen, InteractiveProcessingScreen):
                    await self.push_screen(InteractiveProcessingScreen(image_path=current_image_path, classification_data=extracted_data))
                else: # Pokud už jsme na ní, jen aktualizujeme obsah
                    self.screen.update_content(current_image_path, extracted_data)

            except Exception as e:
                self.notify(f"Neočekávaná chyba: {os.path.basename(current_image_path)}: {e}", severity="error", title="Systémová Chyba")
                self._log_to_screen(f"[bold red]Traceback: {traceback.format_exc()}[/bold red]")
                await self._load_next_interactive_image()
        else:
            self.notify("Všechny obrázky byly zpracovány.", title="Interaktivní Režim Ukončen")
            await self._finalize_interactive_session()
            return # Důležité pro ukončení zde

    async def action_start_interactive_processing(self) -> None:
        input_folder = self.app_settings.get("input_folder")
        if not input_folder or not os.path.isdir(input_folder):
            self.notify(f"Zdrojová složka není nastavena nebo je neplatná: '{input_folder}'", severity="error", title="Chyba Vstupu")
            return
        self.interactive_image_paths = find_images(input_folder)
        if not self.interactive_image_paths:
            self.notify(f"Ve složce '{input_folder}' nebyly nalezeny žádné obrázky.", title="Info")
            return
        self.current_interactive_index = -1
        self.interactive_results_aggregator = {}
        self.notify(f"Spuštěn interaktivní režim. Nalezeno {len(self.interactive_image_paths)} obrázků.", title="Start")
        await self._load_next_interactive_image()

    async def _finalize_interactive_session(self) -> None:
        output_file = self.app_settings.get("output_file", OUTPUT_FILE)
        tags_file = self.app_settings.get("tags_file", TAGS_FILE)
        if not self.interactive_results_aggregator:
            self._log_to_screen("Nebyly schváleny žádné obrázky k uložení.")
        else:
            self._log_to_screen(f"Ukládám {len(self.interactive_results_aggregator)} výsledků do {output_file}...")
            save_classification_results(output_file, self.interactive_results_aggregator)
            existing_tags_set = set(load_tags(tags_file))
            for item_data in self.interactive_results_aggregator.values():
                if "tagy" in item_data and isinstance(item_data["tagy"], dict):
                    tag_groups = item_data["tagy"]
                    for category_tags_list in tag_groups.values():
                        if isinstance(category_tags_list, list):
                            for tag_val in category_tags_list:
                                if isinstance(tag_val, str) and tag_val:
                                    existing_tags_set.add(tag_val.lower())
            save_tags(tags_file, sorted(list(existing_tags_set)))
            self._log_to_screen(f"Tagy aktualizovány a uloženy do {tags_file}.")
        self.notify("Interaktivní session dokončena.", title="Info")
        if isinstance(self.screen, InteractiveProcessingScreen):
            await self.pop_screen()
        self.interactive_image_paths = []
        self.current_interactive_index = -1
        self.interactive_results_aggregator = {}

    async def _handle_interactive_error_or_end(self) -> None:
        await self._finalize_interactive_session()

    # --- Handlery pro zprávy z InteractiveProcessingScreen ---
    async def on_interactive_processing_screen_approve_message(self, message: ApproveMessage) -> None:
        image_basename = os.path.basename(message.image_path)
        self.interactive_results_aggregator[image_basename] = message.data
        self._log_to_screen(f"[green]Obrázek '{image_basename}' schválen a uložen.[/green]")
        current_categories = message.data.get("kategorie", [])
        if current_categories:
            categories_folder_path = self.app_settings.get("categories_folder", CATEGORIES_FOLDER)
            organize_file_into_category_folders( 
                message.image_path, current_categories, categories_folder_path, image_basename
            )
        await self._load_next_interactive_image()

    async def on_interactive_processing_screen_skip_message(self, message: SkipMessage) -> None:
        image_basename = os.path.basename(message.image_path)
        self._log_to_screen(f"[yellow]Obrázek '{image_basename}' přeskočen.[/yellow]")
        await self._load_next_interactive_image()
    
    async def on_interactive_processing_screen_end_interactive_message(self, message: EndInteractiveMessage) -> None:
        self._log_to_screen("[blue]Ukončuji interaktivní režim...[/blue]")
        await self._finalize_interactive_session()

if __name__ == "__main__":
    app = ImageClassifierApp()
    app.run()
