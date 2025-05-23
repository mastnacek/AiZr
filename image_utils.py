import os
import shutil
import base64
from PIL import Image
from config import console, MAX_SIZE, CACHE_FOLDER # TEMP_FOLDER no longer needed here for resize_image

# Moved from main.py
def get_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".jpg" or ext == ".jpeg":
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    return "application/octet-stream" # Default

def resize_image(image_path: str) -> str:
    """
    Resizes an image if it's larger than MAX_SIZE, using caching.
    Returns path to the (potentially) resized image in CACHE_FOLDER, 
    or original image_path on error.
    """
    try:
        if not os.path.exists(CACHE_FOLDER):
            os.makedirs(CACHE_FOLDER, exist_ok=True)
            console.print(f"Vytvořena složka CACHE_FOLDER: '{CACHE_FOLDER}'")

        image_filename = os.path.basename(image_path)
        cache_path = os.path.join(CACHE_FOLDER, image_filename)

        if os.path.exists(cache_path):
            console.print(f"Použit cachovaný obrázek: '{cache_path}'")
            return cache_path

        img = Image.open(image_path)
        width, height = img.size

        if width <= MAX_SIZE and height <= MAX_SIZE:
            console.print(f"Obrázek '{image_filename}' není třeba zmenšovat. Kopíruji do cache.")
            shutil.copy2(image_path, cache_path)
            return cache_path

        console.print(f"Zmenšuji obrázek '{image_filename}' (rozměry: {width}x{height})...")
        if width > height:
            new_width = MAX_SIZE
            new_height = int((height / width) * MAX_SIZE)
        else:
            new_height = MAX_SIZE
            new_width = int((width / height) * MAX_SIZE)

        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        if resized_img.mode == 'RGBA' and cache_path.lower().endswith(('.jpg', '.jpeg')):
            console.print(f"Převádím RGBA na RGB pro '{cache_path}'")
            resized_img = resized_img.convert('RGB')

        resized_img.save(cache_path)
        console.print(f"Zmenšený obrázek uložen do '{cache_path}'")
        return cache_path

    except FileNotFoundError:
        console.print(f"[bold red]Chyba při změně velikosti: Soubor nenalezen '{image_path}'. Vracím původní cestu.[/bold red]")
        return image_path
    except Exception as e:
        console.print(f"[bold red]Chyba při změně velikosti obrázku '{image_path}': {e}. Vracím původní cestu.[/bold red]")
        return image_path

def find_images(folder_path: str, extensions=('.jpg', '.jpeg', '.png', '.gif'), recursive: bool = True) -> list[str]:
    image_files: list[str] = []
    if not os.path.isdir(folder_path):
        # Předpokládáme, že 'console' je importována v image_utils.py z config
        console.print(f"[error]Zdrojová složka nenalezena: {folder_path}[/error]")
        return image_files

    if recursive:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(extensions):
                    image_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path) and file.lower().endswith(extensions):
                image_files.append(file_path)
    
    search_type = "rekurzivně" if recursive else "nereurzivně"
    # Předpokládáme, že 'console' je importována v image_utils.py z config
    console.print(f"Nalezeno {len(image_files)} obrázků ve složce [path]{folder_path}[/path] (hledáno {search_type}).")
    return image_files

def encode_image(image_path: str) -> tuple[str | None, str | None]:
    """
    Encodes an image to a base64 string and determines its MIME type.
    Returns (base64_string, mime_type) or (None, None) if an error occurs.
    """
    if not image_path or not os.path.exists(image_path): # Check if image_path is valid
        console.print(f"[bold red]Error encoding image: File not found or path is invalid {image_path}[/bold red]")
        return None, None
    try:
        mime_type = get_mime_type(image_path)
        with open(image_path, "rb") as image_file:
            b64_string = base64.b64encode(image_file.read()).decode('utf-8')
        return b64_string, mime_type
    except FileNotFoundError: # Should be caught by os.path.exists, but good for robustness
        console.print(f"[bold red]Error encoding image: File not found {image_path}[/bold red]")
        return None, None
    except Exception as e:
        console.print(f"[bold red]Error encoding image {image_path}: {e}[/bold red]")
        return None, None
