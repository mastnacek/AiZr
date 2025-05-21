import os
import shutil # Included as per requirement, though not used in find_images example
import base64
from PIL import Image
from config import console # For logging within these utility functions

def resize_image(image_path, output_path, size=(1024, 1024)):
    """Resizes an image to a given size."""
    try:
        img = Image.open(image_path)
        img = img.resize(size, Image.Resampling.LANCZOS)
        img.save(output_path)
        console.print(f"Image resized: {image_path} -> {output_path} to {size}")
        return True
    except Exception as e:
        console.print(f"[bold red]Error resizing image {image_path}: {e}[/bold red]")
        return False

def find_images(folder_path, extensions=('.jpg', '.jpeg', '.png', '.gif')):
    """Finds all images with given extensions in a folder."""
    image_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(extensions):
                image_files.append(os.path.join(root, file))
    console.print(f"Found {len(image_files)} images in {folder_path}")
    return image_files

def encode_image(image_path):
    """Encodes an image to a base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        console.print(f"[bold red]Error encoding image {image_path}: {e}[/bold red]")
        return None
