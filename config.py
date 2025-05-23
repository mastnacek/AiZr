import os
import sys
from rich.console import Console

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    console.print("[bold red]Chyba: API klíč OPENROUTER_API_KEY pro výchozího providera není nastaven.[/bold red]")
    sys.exit(1)

# Proměnné pro další API klíče (bez okamžité kontroly)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

HOME_DIR = "/data/data/com.termux/files/home"
INPUT_FOLDER = "/storage/emulated/0/Pictures/facebook"
CATEGORIES_FOLDER = "/storage/emulated/0/Pictures/categories"
OUTPUT_FILE = os.path.join(HOME_DIR, "vystup.json")
TEMP_FOLDER = os.path.join(HOME_DIR, "temp")
CACHE_FOLDER = os.path.join(HOME_DIR, "cache")
TAGS_FILE = os.path.join(HOME_DIR, "tagy.json") 
SETTINGS_FILE = os.path.join(HOME_DIR, "image_classifier_settings.json") # New constant

TEMPERATURE = 0.2
MODEL = "google/gemini-2.5-flash-preview"
MAX_SIZE = 2900

console = Console()
