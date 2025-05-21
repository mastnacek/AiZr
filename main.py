import os 
import sys # Added import for sys.exit
import traceback # For detailed error logging

# TensorFlow and Keras imports (and numpy) are removed as per task.

from config import (
    API_KEY, HOME_DIR, INPUT_FOLDER, CATEGORIES_FOLDER, OUTPUT_FILE,
    TEMP_FOLDER, CACHE_FOLDER, TEMPERATURE, MODEL, MAX_SIZE, console,
    TAGS_FILE
)
from prompts import PROMPT
from image_utils import (
    resize_image,       # Now returns path to resized_img or None
    find_images, 
    encode_image        # Now returns (b64_string, mime_type) or (None, None)
)
from api_client import classify_image as classify_image_api, extract_json
from file_handler import (
    load_tags, 
    save_tags, 
    save_classification_results,
    organize_file_into_category_folders
)

# ImageClassifier class and its associated TensorFlow/Keras/Numpy imports are removed.

def run_classification_process():
    try:
        console.print("[bold blue]Spouštím proces klasifikace obrázků...[/bold blue]")

        existing_tags_list = load_tags(TAGS_FILE)
        existing_tags_set = set(existing_tags_list)
        console.print(f"Načteno {len(existing_tags_set)} existujících tagů.")

        results_aggregator = {}
        
        image_paths = find_images(INPUT_FOLDER)
        if not image_paths:
            console.print(f"[yellow]Nenalezeny žádné obrázky ve složce: {INPUT_FOLDER}. Ukončuji.[/yellow]")
            sys.exit(0)
        
        console.print(f"Nalezeno {len(image_paths)} obrázků ke zpracování.")

        for image_path in image_paths:
            console.print(f"\n[cyan]Zpracovávám {os.path.basename(image_path)}[/cyan]")
            # resized_img_path = None # No longer needed, resize_image always returns a path
            # try: # try block can be removed if finally is the only reason for it, or kept for other exceptions
            
            # resize_image now returns the path to cached/resized image or original on error
            resized_img_path = resize_image(image_path) 
            
            # The check 'if not resized_img_path: continue' is removed as resize_image always returns a path.
            # Errors during resize are logged in resize_image, and it returns original_path as fallback.
            
            console.print(f"Použitá verze obrázku pro API: {os.path.basename(resized_img_path)}")

            b64_image, mime_type = encode_image(resized_img_path) # Returns (b64_str, mime_type) or (None, None)
                if not b64_image:
                    console.print(f"[yellow]Chyba při kódování obrázku {os.path.basename(resized_img_path)}, přeskakuji.[/yellow]")
                    continue # resized_img_path will be cleaned up in finally

                api_response_text = classify_image_api(
                    API_KEY,
                    MODEL,
                    TEMPERATURE,
                    b64_image,
                    mime_type,
                    PROMPT,
                    existing_tags=list(existing_tags_set) 
                )

                if not api_response_text:
                    console.print(f"[yellow]Žádná odpověď z API pro {os.path.basename(image_path)}, přeskakuji.[/yellow]")
                    continue

                extracted_data = extract_json(api_response_text)
                if not extracted_data:
                    console.print(f"[yellow]Nepodařilo se extrahovat JSON pro {os.path.basename(image_path)}, přeskakuji.[/yellow]")
                    continue

                image_basename = os.path.basename(image_path)
                current_categories = extracted_data.get("kategorie", [])

                results_aggregator[image_basename] = {
                    "kategorie": current_categories,
                    "popis": extracted_data.get("popis", ""),
                    "tagy": extracted_data.get("tagy", {}),
                    "text": extracted_data.get("text", "")
                }

                if "tagy" in extracted_data and isinstance(extracted_data["tagy"], dict):
                    tag_groups = extracted_data["tagy"]
                    newly_added_count = 0
                    for category_tags_list in tag_groups.values():
                        if isinstance(category_tags_list, list):
                            for tag in category_tags_list:
                                if isinstance(tag, str) and tag:
                                    processed_tag = tag.lower()
                                    if processed_tag not in existing_tags_set:
                                        newly_added_count +=1
                                    existing_tags_set.add(processed_tag)
                    if newly_added_count > 0:
                         console.print(f"Přidáno {newly_added_count} nových unikátních tagů.")

                if current_categories:
                    organize_file_into_category_folders(
                        image_path, # Original image path for copying
                        current_categories,
                        CATEGORIES_FOLDER,
                        image_basename
                    )
            
            # The finally block for deleting from TEMP_FOLDER is removed as resize_image now uses CACHE_FOLDER.
            # Any specific error handling for the loop's body can be done with a standard try/except if needed,
            # but the original finally was for TEMP_FOLDER cleanup.

        # After the loop
        save_classification_results(OUTPUT_FILE, results_aggregator)
        save_tags(TAGS_FILE, sorted(list(existing_tags_set)))
        console.print(f"\n[bold green]Zpracování dokončeno! Výsledky uloženy do {OUTPUT_FILE} a tagy do {TAGS_FILE}.[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Neočekávaná chyba během zpracování: {e}[/bold red]")
        console.print(f"[bold red]Traceback: {traceback.format_exc()}[/bold red]")
        sys.exit(1)

if __name__ == '__main__':
    run_classification_process()
