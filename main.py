# image_classifier.py (now importing from image_utils)
import os # Still needed for os.path.exists, os.path.join, os.makedirs
# requests, json, re are removed as they are now in api_client.py

import tensorflow as tf
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.preprocessing import image as keras_image # Renamed to avoid conflict with PIL.Image
from tensorflow.keras.applications.resnet50 import preprocess_input, decode_predictions
import numpy as np

from config import (
    API_KEY, HOME_DIR, INPUT_FOLDER, CATEGORIES_FOLDER, OUTPUT_FILE,
    TEMP_FOLDER, CACHE_FOLDER, TEMPERATURE, MODEL, MAX_SIZE, console,
    TAGS_FILE # Import new constant
)
from prompts import PROMPT
from image_utils import resize_image, find_images, encode_image # Import functions
# Import the new API client functions
from api_client import classify_image as classify_image_api, extract_json
from file_handler import (
    load_tags, 
    save_tags, 
    save_classification_results, # Added import
    organize_file_into_category_folders # Added import
)

# Helper function for MIME type (can be moved to image_utils later)
def get_mime_type(image_path: str) -> str:
    ext = os.path.splitext(image_path)[1].lower()
    if ext == ".jpg" or ext == ".jpeg":
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".gif":
        return "image/gif"
    return "application/octet-stream" # Default

class ImageClassifier:
    def __init__(self):
        self.model = ResNet50(weights='imagenet')
        console.print("ImageClassifier initialized.")
        # Example: Potentially use find_images here if the classifier needed to discover images
        # images_in_input = find_images(INPUT_FOLDER)
        # console.print(f"Found {len(images_in_input)} images in input folder during init.")


    def classify_image(self, image_path):
        # Example: Potentially resize or encode image before classification
        # temp_resized_path = os.path.join(TEMP_FOLDER, "temp_resized.jpg")
        # if resize_image(image_path, temp_resized_path):
        #     b64_image = encode_image(temp_resized_path)
        #     # Proceed with classification using b64_image or resized_path
        # else:
        #     console.print(f"Skipping classification for {image_path} due to resize error.")
        #     return []

        img = keras_image.load_img(image_path, target_size=(224, 224)) # Using keras_image
        img_array = keras_image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        img_array = preprocess_input(img_array)
        predictions = self.model.predict(img_array)
        decoded_predictions = decode_predictions(predictions, top=3)[0]
        return decoded_predictions

if __name__ == '__main__':
    # Initialize results aggregator
    results_aggregator = {}

    # Load existing tags and convert to a set for efficient additions
    existing_tags_list = load_tags(TAGS_FILE)
    existing_tags_set = set(existing_tags_list)
    console.print(f"Načtené existující tagy (počet: {len(existing_tags_set)}): {sorted(list(existing_tags_set))[:10]}...") # Print first 10 for brevity

    classifier = ImageClassifier()
    image_path = 'path/to/your/image.jpg' # Replace with actual path

    console.print(f"Classifying image: {image_path} using model: {MODEL}")
    console.print(f"Output will be saved to: {OUTPUT_FILE}")
    console.print(f"Temperature: {TEMPERATURE}, Max Size: {MAX_SIZE}")
    console.print(PROMPT)

    # Example usage of the new functions
    if os.path.exists(image_path):
        # --- Updated API call section ---
        console.print(f"[Main] Attempting API classification for: {image_path}")
        image_b64 = encode_image(image_path) # from image_utils
        if image_b64:
            mime_type = get_mime_type(image_path)
            console.print(f"[Main] Image encoded, MIME type: {mime_type}")
            
            # Call the updated API client function
            # Signature: classify_image(api_key, model, temp, image_b64, mime_type, prompt_template, existing_tags: list[str] = None)
            api_response_text = classify_image_api(
                API_KEY,             # api_key from config
                MODEL,               # model from config
                TEMPERATURE,         # temp from config
                image_b64,           # base64 encoded image
                mime_type,           # determined mime_type
                PROMPT,              # prompt_template from prompts
                existing_tags=existing_tags # loaded tags
            )
            
            if api_response_text:
                console.print(f"[Main] Received API response text.")
                extracted_data = extract_json(api_response_text) # from api_client
                if extracted_data:
                    console.print(f"[Main] Extracted data from API: {extracted_data}")
                    
                    image_basename = os.path.basename(image_path) # Get image basename
                    current_categories = extracted_data.get("kategorie", [])

                    # Store results in aggregator
                    results_aggregator[image_basename] = {
                        "kategorie": current_categories,
                        "popis": extracted_data.get("popis", ""),
                        "tagy": extracted_data.get("tagy", {}),
                        "text": extracted_data.get("text", "")
                    }

                    # Organize file into category folders
                    if current_categories:
                        organize_file_into_category_folders(
                            image_path, 
                            current_categories, 
                            CATEGORIES_FOLDER, 
                            image_basename
                        )
                    
                    # Process and add new tags from API response to the set
                    if "tagy" in extracted_data and isinstance(extracted_data["tagy"], dict):
                        tag_groups = extracted_data["tagy"]
                        newly_added_tags_count = 0
                        for category_tags_list in tag_groups.values():
                            if isinstance(category_tags_list, list):
                                for tag in category_tags_list:
                                    if isinstance(tag, str) and tag: # Add only non-empty strings
                                        processed_tag = tag.lower() # Add tags in lowercase
                                        if processed_tag not in existing_tags_set:
                                            newly_added_tags_count += 1
                                        existing_tags_set.add(processed_tag)
                        if newly_added_tags_count > 0:
                            console.print(f"[Main] Přidáno {newly_added_tags_count} nových unikátních tagů.")
                    else:
                        console.print("[Main] Žádné tagy nebyly v odpovědi API nebo nejsou ve správném formátu.")
                else:
                    console.print("[Main] Failed to extract JSON from API response.")
            else:
                console.print("[Main] No response from API client.")
        else:
            console.print(f"[Main] Failed to encode image {image_path} for API call.")
        # --- End of updated API call section ---

        resized_path = os.path.join(TEMP_FOLDER, "example_resized.jpg")
        if not os.path.exists(TEMP_FOLDER):
            os.makedirs(TEMP_FOLDER)
        
        if resize_image(image_path, resized_path):
            encoded_string = encode_image(resized_path)
            # print(f"Encoded string (first 100 chars): {encoded_string[:100] if encoded_string else 'None'}")
    
        images_found = find_images(INPUT_FOLDER) # Assuming INPUT_FOLDER might contain images
        # console.print(f"Images found by find_images in {INPUT_FOLDER}: {images_found}")

        predictions = classifier.classify_image(image_path)
        print("Predictions:")
        for i, (imagenet_id, label, score) in enumerate(predictions):
            print(f"{i + 1}: {label} ({score:.2f})")
    else:
        console.print(f"[bold red]Error: Image path does not exist: {image_path}[/bold red]")

    # Save the updated set of tags as a sorted list
    save_tags(TAGS_FILE, sorted(list(existing_tags_set)))
    
    # Save aggregated classification results
    save_classification_results(OUTPUT_FILE, results_aggregator)
