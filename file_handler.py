import json
import os
import shutil # Added import
from config import console

def load_tags(filepath: str) -> list[str]:
    """
    Loads a list of tags from a JSON file.
    Returns an empty list if the file doesn't exist or data is invalid.
    """
    if not os.path.exists(filepath):
        console.print(f"[yellow]Warning: Tags file '{filepath}' not found. Starting with an empty list of tags.[/yellow]")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            console.print(f"[yellow]Warning: Tags file '{filepath}' does not contain a list. Starting with an empty list of tags.[/yellow]")
            return []
        # Optionally, further validate if all items in the list are strings
        if not all(isinstance(tag, str) for tag in data):
            console.print(f"[yellow]Warning: Not all items in tags file '{filepath}' are strings. Filtering non-string items.[/yellow]")
            data = [tag for tag in data if isinstance(tag, str)]
        return data
    except FileNotFoundError: # Should be caught by os.path.exists, but good for robustness
        console.print(f"[yellow]Warning: Tags file '{filepath}' not found (FileNotFoundError). Starting with an empty list of tags.[/yellow]")
        return []
    except json.JSONDecodeError:
        console.print(f"[red]Error: Could not decode JSON from tags file '{filepath}'. Starting with an empty list of tags.[/red]")
        return []
    except TypeError as e: # Catch other potential issues like incorrect data types if not a list
        console.print(f"[red]Error: Invalid data type in tags file '{filepath}': {e}. Starting with an empty list of tags.[/red]")
        return []

def save_tags(filepath: str, tags_list: list[str]) -> None:
    """
    Saves a list of tags to a JSON file.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tags_list, f, indent=2, ensure_ascii=False)
        console.print(f"[green]Tags successfully saved to '{filepath}'[/green]")
    except IOError as e:
        console.print(f"[bold red]Error: Could not save tags to file '{filepath}': {e}[/bold red]")
    except TypeError as e: # For issues like non-serializable content if tags_list is not just strings
        console.print(f"[bold red]Error: Could not serialize tags for saving to '{filepath}': {e}[/bold red]")

def save_classification_results(filepath: str, results_data: dict) -> None:
    """
    Saves classification results data to a JSON file.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Classification results successfully saved to '{filepath}'[/green]")
    except IOError as e:
        console.print(f"[bold red]Error: Could not save classification results to file '{filepath}': {e}[/bold red]")
    except TypeError as e: # For issues like non-serializable content
        console.print(f"[bold red]Error: Could not serialize classification results for saving to '{filepath}': {e}[/bold red]")

def organize_file_into_category_folders(
    original_image_path: str, 
    categories: list[str], 
    base_categories_folder: str, 
    image_filename: str
) -> None:
    """
    Copies an image into subfolders corresponding to its categories.
    """
    if not categories:
        console.print(f"[yellow]No categories provided for '{image_filename}', skipping organization.[/yellow]")
        return

    for cat in categories:
        if not cat or not isinstance(cat, str): # Skip empty or invalid category names
            console.print(f"[yellow]Invalid category name '{cat}' for image '{image_filename}', skipping this category.[/yellow]")
            continue
        
        target_category_folder = os.path.join(base_categories_folder, cat)
        destination_path = os.path.join(target_category_folder, image_filename)

        try:
            os.makedirs(target_category_folder, exist_ok=True)
            
            if not os.path.exists(destination_path):
                shutil.copy2(original_image_path, destination_path)
                console.print(f"Copied '{image_filename}' to category '{cat}' folder: '{destination_path}'")
            else:
                console.print(f"File '{image_filename}' already exists in category '{cat}' folder: '{destination_path}', skipping copy.")
        
        except OSError as e: # Catches errors from makedirs like permission issues
            console.print(f"[bold red]OSError creating directory or copying file for category '{cat}': {e}[/bold red]")
        except shutil.Error as e: # Catches errors from shutil.copy2
            console.print(f"[bold red]Shutil.Error copying file for category '{cat}': {e}[/bold red]")
        except Exception as e: # Generic catch-all for other unexpected errors
            console.print(f"[bold red]Unexpected error organizing file for category '{cat}': {e}[/bold red]")
