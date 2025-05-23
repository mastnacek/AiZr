from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
# DOMQuery se typicky nepoužívá přímo v kódu widgetu, ale pro dotazy na DOM,
# takže ho prozatím odstraníme z importů, pokud není explicitně potřeba.
# from textual.css.query import DOMQuery 
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, Select, Input, Switch, Label
from textual.message import Message # Potřebné pro Select.Changed
from typing import Optional # Potřebné pro Optional[str]

# Na začátek souboru screens/settings_screen.py
from config import INPUT_FOLDER, CATEGORIES_FOLDER, CACHE_FOLDER, MAX_SIZE # MODEL a TEMPERATURE nejsou zde přímo potřeba

# Jednoduché CSS pro SettingsScreen
SETTINGS_SCREEN_CSS = """
SettingsScreen {
    align: center top;
}
#settings-container {
    width: 80%;
    max-width: 70;
    height: auto;
    margin-top: 2;
    padding: 1 2;
    border: round $primary;
    background: $panel-darken-1;
}
.setting-row {
    layout: horizontal;
    align: middle left;
    height: auto;
    margin-bottom: 1;
}
.setting-row Label {
    width: 30%;
    margin-right: 1;
}
.setting-row Input, .setting-row Select {
    width: 70%;
}
.setting-row Switch {
    width: auto;
}
#buttons-container {
    padding-top: 1;
    align: center middle; /* Oprava: align je pro layout, ne pro widget přímo */
    /* Pro centrování tlačítek můžeme použít kontejner s align, nebo nastavit marginy na tlačítkách */
}
.section-title { /* Přidáno pro lepší vizuální oddělení sekcí */
    padding-top: 1;
    padding-bottom: 1;
    text-style: bold;
    width: 100%;
    text-align: center;
}
"""

class SettingsScreen(Screen):
    CSS = SETTINGS_SCREEN_CSS
    BINDINGS = [
        ("escape", "pop_screen", "Zpět"),
    ]
    AI_PROVIDERS = [
        ("OpenRouter", "openrouter"),
        ("Ollama (Local)", "ollama"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(name="Nastavení Aplikace")
        with Vertical(id="settings-container"):
            yield Static("Konfigurace AI Providera:", classes="section-title")
            with Horizontal(classes="setting-row"):
                yield Label("AI Provider:")
                yield Select(self.AI_PROVIDERS, value="openrouter", id="ai_provider_select")
            with Horizontal(classes="setting-row"):
                yield Label("Model:")
                yield Select([("Načítání modelů...", "")], id="model_select", disabled=True)

            yield Static("Nastavení Zpracování Obrázků:", classes="section-title")
            with Horizontal(classes="setting-row"):
                yield Label("Max. velikost (px):")
                yield Input(placeholder="např. 2000", id="max_image_size", value=str(MAX_SIZE)) # MAX_SIZE je int
            with Horizontal(classes="setting-row"):
                yield Label("Rekurzivní hledání:")
                yield Switch(value=True, id="recursive_search")

            yield Static("Nastavení Cest:", classes="section-title")
            with Horizontal(classes="setting-row"):
                yield Label("Zdrojová složka:")
                yield Input(placeholder="/cesta/ke/zdroji", id="input_folder", value=INPUT_FOLDER)
            with Horizontal(classes="setting-row"):
                yield Label("Výstupní složka:")
                yield Input(placeholder="/cesta/pro/kategorie", id="categories_folder", value=CATEGORIES_FOLDER)
            with Horizontal(classes="setting-row"):
                yield Label("Složka pro cache:")
                yield Input(placeholder="/cesta/pro/cache", id="cache_folder", value=CACHE_FOLDER)
            
            with Horizontal(id="buttons-container"): # Tento kontejner můžeme ostylovat pro centrování
                yield Button("Uložit nastavení", id="save_settings", variant="primary")
                yield Button("Zpět", id="cancel_settings", variant="default")
        yield Footer()

    async def update_model_choices(self, provider_id: Optional[str]) -> None:
        model_select = self.query_one("#model_select", Select)
        if not provider_id:
            model_select.set_options([("Vyberte providera", "")])
            model_select.disabled = True
            model_select.value = None
            return

        # Kontrola, zda self.app a self.app.providers_registry existují
        if not hasattr(self.app, 'providers_registry') or not self.app.providers_registry:
            self.app.notify("Chyba: Registr providerů není inicializován v aplikaci.", severity="error", title="Chyba Providerů")
            model_select.set_options([("Chyba: Registr providerů", "")])
            model_select.disabled = True
            model_select.value = None
            return
            
        provider = self.app.providers_registry.get(str(provider_id)) # provider_id může být typu Unknown
        if not provider:
            model_select.set_options([("Chyba: Provider nenalezen", "")])
            model_select.disabled = True
            model_select.value = None
            return

        try:
            models = provider.load_models() # Tato metoda by měla být rychlá nebo asynchronní
            
            if not models:
                model_options = [("Žádné modely nenalezeny", "")]
                model_select.value = None
            else:
                model_options = [(f"{m['name']}", str(m['id'])) for m in models]
                
                current_model_id_for_provider = None
                # Zkusíme získat model uložený pro tohoto konkrétního providera
                if hasattr(self.app, 'app_settings') and self.app.app_settings:
                    current_model_id_for_provider = self.app.app_settings.get(f"{provider_id}_model_id")
                    # Pokud není specifický model, zkusíme obecný model_id, pokud provider odpovídá
                    if not current_model_id_for_provider and self.app.app_settings.get("ai_provider_id") == provider_id:
                        current_model_id_for_provider = self.app.app_settings.get("model_id")
                
                if current_model_id_for_provider and any(opt[1] == current_model_id_for_provider for opt in model_options):
                    model_select.value = current_model_id_for_provider
                elif model_options: 
                    model_select.value = model_options[0][1] 
                else: 
                    model_select.value = None

            model_select.set_options(model_options)
            model_select.disabled = False if models else True

        except Exception as e:
            self.app.notify(f"Chyba načítání modelů pro {provider_id}: {e}", severity="error", title="Chyba Modelů")
            model_select.set_options([("Chyba načítání", "")])
            model_select.disabled = True
            model_select.value = None
            
    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "ai_provider_select":
            # event.value je již hodnota vybrané možnosti (ID providera)
            await self.update_model_choices(str(event.value) if event.value is not None else None)

    async def on_mount(self) -> None: # Změna na async
        if hasattr(self.app, 'app_settings') and self.app.app_settings:
            current_settings = self.app.app_settings
            self.query_one("#ai_provider_select", Select).value = current_settings.get("ai_provider_id", "openrouter")
            self.query_one("#max_image_size", Input).value = str(current_settings.get("max_image_size", MAX_SIZE))
            self.query_one("#recursive_search", Switch).value = current_settings.get("recursive_search", True)
            self.query_one("#input_folder", Input).value = current_settings.get("input_folder", INPUT_FOLDER)
            self.query_one("#categories_folder", Input).value = current_settings.get("categories_folder", CATEGORIES_FOLDER)
            self.query_one("#cache_folder", Input).value = current_settings.get("cache_folder", CACHE_FOLDER)
            
            # Načti modely pro aktuálně vybraného providera
            # Hodnota Select widgetu je již nastavena, takže ji můžeme použít
            selected_provider_id = self.query_one("#ai_provider_select", Select).value
            await self.update_model_choices(str(selected_provider_id) if selected_provider_id is not None else None)

            # Nastav vybraný model, pokud existuje v app_settings a je pro aktuálního providera
            # Toto je již ošetřeno v update_model_choices, které se snaží zachovat hodnotu.
            # Ale pro explicitní nastavení z 'model_id' po načtení options:
            model_select = self.query_one("#model_select", Select)
            if current_settings.get("ai_provider_id") == selected_provider_id:
                model_to_set = current_settings.get("model_id")
                if model_to_set and any(opt[1] == model_to_set for opt in model_select._options):
                     model_select.value = model_to_set
        else:
            # Fallback, pokud app_settings nejsou k dispozici
            await self.update_model_choices(self.query_one("#ai_provider_select", Select).value)


    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_settings":
            self.app.pop_screen()
        elif event.button.id == "save_settings":
            settings_data = {
                "ai_provider_id": str(self.query_one("#ai_provider_select", Select).value) if self.query_one("#ai_provider_select", Select).value else None,
                "model_id": str(self.query_one("#model_select", Select).value) if self.query_one("#model_select", Select).value else None,
                "max_image_size": int(self.query_one("#max_image_size", Input).value or "0"),
                "recursive_search": self.query_one("#recursive_search", Switch).value,
                "input_folder": self.query_one("#input_folder", Input).value,
                "categories_folder": self.query_one("#categories_folder", Input).value,
                "cache_folder": self.query_one("#cache_folder", Input).value,
            }
            if hasattr(self.app, 'update_app_settings'):
                self.app.update_app_settings(settings_data)
                self.app.notify("Nastavení uložena.", title="Úspěch")
            else:
                self.app.notify("Chyba: Metoda pro aktualizaci nastavení chybí v aplikaci.", title="Chyba", severity="error")
            self.app.pop_screen()
```
