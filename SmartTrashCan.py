import os
import time
import json
from datetime import datetime, timedelta
import cv2
from google.cloud import vision
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

# Initialize local LLaMA model
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_threads=4,
    n_gpu_layers=0
)

class SmartTrashCan:
    def __init__(self):
        self.camera = cv2.VideoCapture(CAMERA_ID)
        self.database_path = os.path.join(STORAGE_PATH, "items_database.json")
        self.items_database = self._load_database()
        
    def _load_database(self):
        """Load existing database or create a new one"""
        if os.path.exists(self.database_path):
            with open(self.database_path, 'r') as f:
                return json.load(f)
        return {
            "items": [],
            "statistics": {
                "total_items": 0,
                "total_carbon_footprint": 0,
                "categories": {
                    "recyclable": 0,
                    "compostable": 0,
                    "hazardous": 0,
                    "general": 0
                },
                "item_types": {}
            }
        }
    
    def _save_database(self):
        """Save the database to disk"""
        with open(self.database_path, 'w') as f:
            json.dump(self.items_database, f, indent=2)
    
    def capture_image(self):
        """Capture an image from the camera"""
        print("Capturing image...")
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
        
        # Updated prompt with your specific questions
        prompt = f"""
        The following items were detected in a trash can: {', '.join(objects)}
        
        Please analyze this trash item and provide the following information in JSON format:
        
        1. waste_category: What category of waste is this? Choose one: "recyclable", "compostable", "hazardous", or "general".
        2. production_emissions: Estimated CO2e (carbon equivalent) emissions from producing this item (in kg).
        3. disposal_emissions: Estimated CO2e emissions from improper disposal (e.g., landfill) (in kg).
        4. recommended_disposal: Recommended disposal method (e.g., curbside recycling, e-waste center, compost bin).
        5. decomposition_time: Estimated decomposition time (e.g., "450 years", "6 months").
        
        Respond with a valid JSON object containing only these five fields, with no additional text or explanation.
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
        
        # Try to parse as JSON
        try:
            analysis = json.loads(llm_response)
            # Ensure all required fields are present
            required_fields = ["waste_category", "production_emissions", "disposal_emissions", 
                              "recommended_disposal", "decomposition_time"]
            
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = "Unknown"
                    
            return analysis
            
        except json.JSONDecodeError:
            # If JSON parsing fails, create a structured response from the text
            print("Failed to parse LLM response as JSON. Creating structured response...")
            return {
                "waste_category": "unknown",
                "production_emissions": "unknown",
                "disposal_emissions": "unknown",
                "recommended_disposal": "unknown",
                "decomposition_time": "unknown",
                "raw_analysis": llm_response
            }
    
    def process_new_item(self):
        """Process a new item being thrown away"""
        # Step 1: Capture image
        image_path = self.capture_image()
        if not image_path:
            return None
        
        # Step 2: Detect objects with Google Cloud Vision
        detected_objects = self.detect_object(image_path)
        if not detected_objects:
            print("No objects detected")
            return None
            
        # Step 3: Analyze with local LLM
        analysis = self.analyze_with_llm(detected_objects)
        
        # Step 4: Store the information
        timestamp = datetime.now().isoformat()
        item_data = {
            "id": len(self.items_database["items"]) + 1,
            "timestamp": timestamp,
            "image_path": image_path,
            "detected_objects": detected_objects,
            "waste_category": analysis.get("waste_category", "unknown"),
            "production_emissions": analysis.get("production_emissions", "unknown"),
            "disposal_emissions": analysis.get("disposal_emissions", "unknown"),
            "recommended_disposal": analysis.get("recommended_disposal", "unknown"),
            "decomposition_time": analysis.get("decomposition_time", "unknown")
        }
        
        # Add to items list
        self.items_database["items"].append(item_data)
        
        # Update statistics
        self._update_statistics(item_data)
        
        # Save database
        self._save_database()
        print(f"Item #{item_data['id']} processed and saved to database")
        
        return item_data
    
    def _update_statistics(self, item_data):
        """Update statistics based on new item"""
        stats = self.items_database["statistics"]
        
        # Increment total items
        stats["total_items"] += 1
        
        # Update category counts
        category = item_data["waste_category"].lower()
        if category in stats["categories"]:
            stats["categories"][category] += 1
        else:
            # If somehow the category is not one of our predefined ones
            stats["categories"]["general"] += 1
        
        # Update item types frequency
        primary_object = item_data["detected_objects"][0] if item_data["detected_objects"] else "Unknown"
        if primary_object in stats["item_types"]:
            stats["item_types"][primary_object] += 1
        else:
            stats["item_types"][primary_object] = 1
        
        # Update carbon footprint
        try:
            # Try to extract numeric value from emissions string
            production_emission = self._extract_numeric_value(item_data["production_emissions"])
            stats["total_carbon_footprint"] += production_emission
        except:
            # If we can't parse the emissions, don't update the total
            pass
    
    def _extract_numeric_value(self, emission_string):
        """Extract numeric value from a string like '0.08 kg'"""
        try:
            return float(''.join(c for c in emission_string if c.isdigit() or c == '.'))
        except:
            return 0
    
    def get_statistics(self, period="all"):
        """Get statistics for a specific time period"""
        stats = {
            "itemCount": 0,
            "carbonFootprint": 0,
            "categories": {
                "recyclable": 0,
                "compostable": 0,
                "hazardous": 0,
                "general": 0
            },
            "topItems": []
        }
        
        # Calculate start date based on period
        now = datetime.now()
        start_date = None
        
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())  # Monday of current week
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Filter items by date if needed
        filtered_items = self.items_database["items"]
        if start_date:
            filtered_items = [
                item for item in self.items_database["items"]
                if datetime.fromisoformat(item["timestamp"]) >= start_date
            ]
        
        # Count items in period
        stats["itemCount"] = len(filtered_items)
        
        # Calculate carbon footprint
        carbon_footprint = 0
        category_counts = {"recyclable": 0, "compostable": 0, "hazardous": 0, "general": 0}
        item_types = {}
        
        for item in filtered_items:
            # Add to carbon footprint
            try:
                emission = self._extract_numeric_value(item["production_emissions"])
                carbon_footprint += emission
            except:
                pass
            
            # Add to category counts
            category = item["waste_category"].lower()
            if category in category_counts:
                category_counts[category] += 1
            else:
                category_counts["general"] += 1
            
            # Count item types
            if item["detected_objects"]:
                primary_object = item["detected_objects"][0]
                if primary_object in item_types:
                    item_types[primary_object] += 1
                else:
                    item_types[primary_object] = 1
        
        stats["carbonFootprint"] = f"{carbon_footprint:.2f} kg"
        stats["categories"] = category_counts
        
        # Get top items
        top_items = sorted(item_types.items(), key=lambda x: x[1], reverse=True)[:5]
        stats["topItems"] = [{"name": item[0], "count": item[1]} for item in top_items]
        
        return stats
    
    def search_item(self, keyword):
        """Search for items in the database matching a keyword"""
        results = []
        
        for item in self.items_database["items"]:
            # Search in detected objects
            if any(keyword.lower() in obj.lower() for obj in item["detected_objects"]):
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
                item_data = self.process_new_item()
                if item_data:
                    print(f"Item analysis complete: {item_data['waste_category']}")
                
        except KeyboardInterrupt:
            print("Shutting down Smart Trash Can")
            self.camera.release()
            
    def get_item_by_id(self, item_id):
        """Get an item by its ID"""
        for item in self.items_database["items"]:
            if item["id"] == item_id:
                return item
        return None

# For testing purposes
if __name__ == "__main__":
    trash_can = SmartTrashCan()
    trash_can.run_detection_loop()