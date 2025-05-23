import os # Přidáno pro os.path.basename
from typing import Dict, Any 
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, Label
from textual.message import Message # Přidáno pro vlastní zprávy

INTERACTIVE_CSS = """
InteractiveProcessingScreen {
    align: center top;
}
#interactive-container {
    width: 90%;
    max-width: 90;
    height: auto;
    margin-top: 1;
    padding: 1;
    border: round $primary;
    background: $panel-darken-1;
}
#image-path-display {
    width: 100%;
    padding: 0 1;
    margin-bottom: 1;
    border: panel $background-lighten-2;
    color: $text-muted;
}
.detail-row {
    layout: horizontal;
    align: top left;
    height: auto;
    margin-bottom: 1;
}
.detail-row Label {
    width: 25%;
    margin-right: 1;
    text-style: bold;
}
.detail-row Static {
    width: 75%;
    height: auto;
}
#interactive-buttons-container {
    padding-top: 1;
    layout: horizontal;
    width: 100%;
    align-horizontal: center;
}
#interactive-buttons-container Button {
    margin: 0 1;
}
"""

class InteractiveProcessingScreen(Screen):
    CSS = INTERACTIVE_CSS

    BINDINGS = [
        ("a", "approve", "Schválit"),
        ("s", "skip", "Přeskočit"),
        ("u", "edit_categories", "Upravit Kat."),
        ("x", "end_interactive", "Ukončit Inter."),
    ]
    
    # Definice vlastních zpráv pro komunikaci s ImageClassifierApp
    # Musí být definovány zde nebo importovány, pokud je má App zachytávat
    class ApproveMessage(Message):
        def __init__(self, image_path: str, data: Dict[str, Any]):
            self.image_path = image_path
            self.data = data
            super().__init__()

    class SkipMessage(Message):
        def __init__(self, image_path: str):
            self.image_path = image_path
            super().__init__()
    
    class EndInteractiveMessage(Message):
        pass

    def __init__(self, image_path: str = "", classification_data: Dict[str, Any] = None, name: str = None, id: str = None, classes: str = None):
        super().__init__(name=name, id=id, classes=classes)
        self._image_path = image_path
        self._classification_data = classification_data if classification_data else {}

    def compose(self) -> ComposeResult:
        yield Header(name=f"Interaktivní: {os.path.basename(self._image_path) if self._image_path else 'Načítání...'}")
        with VerticalScroll(id="interactive-container"):
            yield Static(f"Soubor: {self._image_path}", id="image-path-display")
            with Horizontal(classes="detail-row"):
                yield Label("Kategorie:")
                yield Static("", id="interactive_kategorie")
            with Horizontal(classes="detail-row"):
                yield Label("Popis:")
                yield Static("", id="interactive_popis")
            with Horizontal(classes="detail-row"):
                yield Label("Tagy:")
                yield Static("", id="interactive_tagy")
            with Horizontal(classes="detail-row"):
                yield Label("Extrahovaný text:")
                yield Static("", id="interactive_text")
        with Horizontal(id="interactive-buttons-container"):
            yield Button("Schválit a Další", id="approve_next", variant="success")
            yield Button("Přeskočit", id="skip", variant="warning")
            yield Button("Upravit Kategorie", id="edit_categories", variant="default", disabled=True)
            yield Button("Ukončit Interaktivní", id="end_interactive", variant="error")
        yield Footer()

    # Metody, které se mají přidat nebo nahradit, pokud existují jako komentáře:

    def on_mount(self) -> None:
        self.update_content(self._image_path, self._classification_data)

    def _format_tags(self, tags_data: Dict[str, Any]) -> str:
        if not isinstance(tags_data, dict):
            return "N/A"
        lines = []
        for category, tags_list in tags_data.items():
            if isinstance(tags_list, list) and tags_list:
                lines.append(f"  [b]{category.capitalize()}[/b]: {', '.join(tags_list)}")
        return "\n".join(lines) if lines else "Žádné tagy."

    def update_content(self, image_path: str, classification_data: Dict[str, Any]) -> None:
        self._image_path = image_path
        self._classification_data = classification_data if classification_data else {}
        try:
            header = self.query_one(Header)
            header.name = f"Interaktivní: {os.path.basename(image_path) if image_path else 'Neznámý soubor'}"
        except Exception:
            pass
        self.query_one("#image-path-display", Static).update(f"Soubor: {image_path if image_path else 'N/A'}")
        kategorie_str = ", ".join(self._classification_data.get("kategorie", ["N/A"]))
        self.query_one("#interactive_kategorie", Static).update(kategorie_str)
        self.query_one("#interactive_popis", Static).update(self._classification_data.get("popis", "N/A"))
        tagy_formatted = self._format_tags(self._classification_data.get("tagy", {}))
        self.query_one("#interactive_tagy", Static).update(tagy_formatted)
        self.query_one("#interactive_text", Static).update(self._classification_data.get("text", "N/A"))

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve_next":
            self.app.post_message(self.ApproveMessage(self._image_path, self._classification_data))
        elif event.button.id == "skip":
            self.app.post_message(self.SkipMessage(self._image_path))
        elif event.button.id == "edit_categories":
            self.app.notify("Funkce 'Upravit Kategorie' bude implementována později.", title="Info")
        elif event.button.id == "end_interactive":
            self.app.post_message(self.EndInteractiveMessage())
    
    def action_approve(self) -> None:
        if self._image_path: # Ensure there's an image to approve
            self.app.post_message(self.ApproveMessage(self._image_path, self._classification_data))

    def action_skip(self) -> None:
        if self._image_path: # Ensure there's an image to skip
            self.app.post_message(self.SkipMessage(self._image_path))

    def action_edit_categories(self) -> None:
        self.app.notify("Funkce 'Upravit Kategorie' bude implementována později.", title="Info")

    def action_end_interactive(self) -> None:
        self.app.post_message(self.EndInteractiveMessage())
```
