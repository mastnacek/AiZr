import os
import sys
from rich.console import Console

API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("Chyba: API klíč OPENROUTER_API_KEY není nastaven.")
    sys.exit(1)

HOME_DIR = "/data/data/com.termux/files/home"
INPUT_FOLDER = "/storage/emulated/0/Pictures/facebook"
CATEGORIES_FOLDER = "/storage/emulated/0/Pictures/categories"
OUTPUT_FILE = os.path.join(HOME_DIR, "vystup.json")
TEMP_FOLDER = os.path.join(HOME_DIR, "temp")
CACHE_FOLDER = os.path.join(HOME_DIR, "cache")
TAGS_FILE = os.path.join(HOME_DIR, "tagy.json") # New constant

TEMPERATURE = 0.2
MODEL = "google/gemini-2.5-flash-preview"
MAX_SIZE = 2900

console = Console()
