import os
import time
import json
from datetime import datetime
import cv2
from google.cloud import vision
import torch
from llama_cpp import Llama

# Configuration
CAMERA_ID = 0
STORAGE_PATH = "/Users/jayvenkatesh/Downloads/trashimages"
CREDENTIALS_PATH = "/Users/jayvenkatesh/Downloads/ambient-shelter-457900-n8-eca6c50e1677.json"
MODEL_PATH = "/Users/jayvenkatesh/smart_trash_can/models/llama-2-7b.Q4_K_M.gguf"

# Ensure storage directory exists
os.makedirs(STORAGE_PATH, exist_ok=True)

# Initialize Google Cloud Vision client
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_PATH
vision_client = vision.ImageAnnotatorClient()

# Initialize local LLaMA model (for GGUF format)
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,     # Context window
    n_threads=4,    # Number of CPU threads to use
    n_gpu_layers=0  # Set higher (e.g., 32) if you have a good GPU
)

class SmartTrashCan:
    def __init__(self):
        self.camera = cv2.VideoCapture(CAMERA_ID)
        self.items_database = self._load_database()
        
    def _load_database(self):
        """Load existing database or create a new one"""
        db_path = os.path.join(STORAGE_PATH, "items_database.json")
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                return json.load(f)
        return {"items": []}
    
    def _save_database(self):
        """Save the database to disk"""
        db_path = os.path.join(STORAGE_PATH, "items_database.json")
        with open(db_path, 'w') as f:
            json.dump(self.items_database, f, indent=2)
    
    def capture_image(self):
        """Capture an image from the camera"""
        print("Motion detected! Capturing image...")
        ret, frame = self.camera.read()
        if not ret:
            print("Failed to capture image")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = os.path.join(STORAGE_PATH, f"item_{timestamp}.jpg")
        cv2.imwrite(image_path, frame)
        print(f"Image saved to {image_path}")
        return image_path
    
    def detect_object(self, image_path):
        """Use Google Cloud Vision to detect objects in the image"""
        print("Detecting objects with Google Cloud Vision...")
        with open(image_path, "rb") as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = vision_client.label_detection(image=image)
        labels = response.label_annotations
        
        objects = [label.description for label in labels]
        print(f"Detected objects: {', '.join(objects)}")
        return objects
    
    def analyze_with_llm(self, objects):
        """Use local LLaMA model to analyze the detected objects"""
        print("Analyzing with local LLaMA model...")
        
        # Construct a prompt for the LLM
        prompt = f"""
        The following items were detected in a trash can: {', '.join(objects)}
        
        Please provide the following information:
        1. What category of waste is this (recyclable, compostable, hazardous, general waste)?
        2. Environmental impact of disposing this item
        3. Better alternatives for disposal if applicable
        4. Estimated decomposition time
        
        Respond in JSON format with the fields: category, environmental_impact, better_disposal, decomposition_time
        """
        
        # Get response from local LLM
        response = llm(
            prompt,
            max_tokens=512,
            stop=["</s>", "\n\n"],
            echo=False
        )
        
        llm_response = response['choices'][0]['text'].strip()
        print(f"LLM Analysis: {llm_response}")
        
        # Try to parse as JSON, if fails return as text
        try:
            return json.loads(llm_response)
        except json.JSONDecodeError:
            return {"analysis": llm_response}
    
    def process_new_item(self):
        """Process a new item being thrown away"""
        # Step 1: Capture image
        image_path = self.capture_image()
        if not image_path:
            return
        
        # Step 2: Detect objects with Google Cloud Vision
        detected_objects = self.detect_object(image_path)
        if not detected_objects:
            print("No objects detected")
            return
            
        # Step 3: Analyze with local LLM
        analysis = self.analyze_with_llm(detected_objects)
        
        # Step 4: Store the information
        timestamp = datetime.now().isoformat()
        item_data = {
            "id": len(self.items_database["items"]) + 1,
            "timestamp": timestamp,
            "image_path": image_path,
            "detected_objects": detected_objects,
            "analysis": analysis
        }
        
        self.items_database["items"].append(item_data)
        self._save_database()
        print(f"Item #{item_data['id']} processed and saved to database")
        return item_data
    
    def search_item(self, keyword):
        """Search for items in the database matching a keyword"""
        results = []
        
        for item in self.items_database["items"]:
            # Search in detected objects
            if any(keyword.lower() in obj.lower() for obj in item["detected_objects"]):
                results.append(item)
            
            # Search in analysis text if it's stored as text
            if isinstance(item["analysis"], dict) and "analysis" in item["analysis"]:
                if keyword.lower() in item["analysis"]["analysis"].lower():
                    if item not in results:
                        results.append(item)
        
        return results
    
    def run_detection_loop(self):
        """Main loop for detecting items"""
        print("Smart Trash Can is running. Press Ctrl+C to stop.")
        try:
            while True:
                # In a real implementation, you would have motion detection here
                # For simplicity, we'll just wait for user input
                input("Press Enter to simulate throwing away an item...")
                self.process_new_item()
                
        except KeyboardInterrupt:
            print("Shutting down Smart Trash Can")
            self.camera.release()

# For testing purposes
if __name__ == "__main__":
    trash_can = SmartTrashCan()
    trash_can.run_detection_loop()