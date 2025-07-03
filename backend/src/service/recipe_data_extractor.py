import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class RecipeDataExtractor:
    """
    A class responsible for extracting and formatting recipe data from the knowledge graph JSON file.
    """
    def __init__(self, kg_path: str):
        """
        Initializes the extractor by loading the knowledge graph data from a file.

        Args:
            kg_file_path (str): The path to the knowledge graph JSON file.
        """
        self.kg_path = kg_path
        print(f"Initializing RecipeDataExtractor with kg_path: {self.kg_path}")
        self.data = self._load_data()
        if self.data:
            logger.info(f"RecipeDataExtractor initialized successfully with data from '{kg_path}'.")
        else:
            logger.error(f"RecipeDataExtractor failed to initialize. Could not load data from '{kg_path}'.")

    def _load_data(self) -> Optional[Dict]:
        """Loads the JSON data from the file specified during initialization."""
        try:
            with open(self.kg_path, 'r', encoding='utf-8') as f:
                data = []
                for line in f:
                    data.append(json.loads(line))
                return data
        except FileNotFoundError:
            logger.error(f"Knowledge graph file not found at: {self.kg_path}")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from: {self.kg_path}")
        return None
    
    def _process_dish_data(self, dish_url: str, dish_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms a single raw dish data dictionary into the desired format,
        including the dish URL.

        Args:
            dish_url (str): The URL of the dish being processed.
            dish_data (Dict[str, Any]): The raw data dictionary for the dish.

        Returns:
            A dictionary containing the formatted dish information.
        """
        # --- Extract Ingredient Names ---
        raw_ingredients = dish_data.get("neighbors", {}).get("contains_ingredients", [])
        ingredient_names = []
        for ingredient_entry in raw_ingredients:
            # Each entry is a dict with the ingredient URI as the key
            for ingredient_details in ingredient_entry.values():
                name_list = ingredient_details.get("name", [])
                if name_list:
                    cleaned_name = name_list[0].replace('\\', '')
                    ingredient_names.append(cleaned_name)

        # --- Extract Nutrition Information ---
        neighbors = dish_data.get("neighbors", {})
        nutrition_keys = [
            "calories", "protein", "carbohydrates", 
            "saturated fat", "monounsaturated fat", "polyunsaturated fat"
        ]
        nutrition_info = {}
        for key in nutrition_keys:
            if key in neighbors:
                try:
                    amount_str = neighbors[key][0]
                    nutrition_info[key] = float(amount_str)
                except (ValueError, IndexError):
                    nutrition_info[key] = None

        return {
            "dish_url": dish_url,  # <-- Added this line
            "dish_name": dish_data.get('name', ['Unknown Dish'])[0].replace('\\', ''),
            "ingredients": sorted(ingredient_names),
            "nutrition": nutrition_info
        }

    def get_dishes_by_urls(self, tag_url: str, dish_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Extracts and formats information for a list of dishes under a specific tag.
        """
        results = []
        if not self.data:
            logger.warning("Cannot get dishes; KG data is not loaded.")
            return results

        tag_data = None
        for entry in self.data:
            if tag_url in entry:
                tag_data = entry[tag_url]
                break
        if tag_data is None:
            logger.warning(f"Tag URL '{tag_url}' not found in the knowledge graph.")
            return results

        tagged_dishes = tag_data.get("neighbors", {}).get("tagged_dishes", [])


        if tag_data is None:
            print(f"Error: Tag URL '{tag_url}' not found in the JSON file.")
            return results

        tagged_dishes = tag_data.get("neighbors", {}).get("tagged_dishes", [])
        
        # Create a lookup map for efficient searching
        dishes_map = {k: v for dish_entry in tagged_dishes for k, v in dish_entry.items()}

        for url in dish_urls: 
            if url in dishes_map:
                raw_dish_data = dishes_map[url]
                # Pass the dish URL to the processing function
                processed_data = self._process_dish_data(url, raw_dish_data)
                results.append(processed_data)
            else:
                logger.warning(f"Dish URL '{url}' not found under the tag '{tag_url}'.")
        
        return results