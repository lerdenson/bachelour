from service.BAMnet.src.core.kbqa import KBQA
from config import config
from typing import List, Dict, Any, Optional

import json

def _process_dish_data(dish_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms a single raw dish data dictionary into the desired format
    with a list of ingredient names and a dictionary of nutrition info.
    """
    # --- Extract Ingredient Names ---
    raw_ingredients = dish_data.get("neighbors", {}).get("contains_ingredients", [])
    ingredient_names = []
    for ingredient_entry in raw_ingredients:
        # Each entry is a dict with the ingredient URI as the key
        for ingredient_details in ingredient_entry.values():
            name_list = ingredient_details.get("name", [])
            if name_list:
                # Clean up the name (remove extra slashes) and add to the list
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
            # The value is a list with one string element, convert it to float
            try:
                amount_str = neighbors[key][0]
                nutrition_info[key] = float(amount_str)
            except (ValueError, IndexError):
                # Handle cases where the value is not a valid number or the list is empty
                nutrition_info[key] = None

    return {
        "dish_name": dish_data.get('name', ['Unknown Dish'])[0].replace('\\', ''),
        "ingredients": sorted(ingredient_names), # Sort for consistent order
        "nutrition": nutrition_info
    }

def extract_dishes_info(
    file_path: str, 
    tag_url: str, 
    dish_urls: List[str]
) -> List[Dict[str, Any]]:
    """
    Extracts and formats information for a list of dishes from a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        tag_url (str): The URL of the tag to search within.
        dish_urls (List[str]): A list of dish URLs to extract.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing the
                               formatted ingredient and nutrition info for a found dish.
    """
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                data.append(json.loads(line))
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return results
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON file.")
        return results

    tags = set()
    for entry in data:
        for key, value in entry.items():
            tags.add(key)


    # Create a lookup map for efficient searching

if __name__ == '__main__':
    json_file = config['kb_path']  # Path to the JSON file containing dish data


    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                data.append(json.loads(line))
    except FileNotFoundError:
        print(f"Error: The file '{json_file}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{json_file}' is not a valid JSON file.")

    tags = set()
    for entry in data:
        for key, value in entry.items():
            tags.add(key.replace('http://idea.rpi.edu/heals/kb/tag/', ''))  # Clean up tag names by removing backslashes

    print(f'number of tags found: {len(tags)}')
    print(f"Tags found in the file: {tags}")


    # tag_url_to_find = 'http://idea.rpi.edu/heals/kb/tag/baja'

    # # List of dish URLs to find and process
    # dish_urls_to_find = [
    #     'http://idea.rpi.edu/heals/kb/recipe/ab7f7073-Baja%20Fried-Fish%20Tacos',
    #     'http://idea.rpi.edu/heals/kb/recipe/6c299d01-Xochipilli%27s%20Guacamole%20Ole',
    #     'http://idea.rpi.edu/heals/kb/recipe/invalid-url-for-testing' # This one will not be found
    # ]

    # # Get the processed information for the list of dishes
    # dishes_information = extract_dishes_info(json_file, tag_url_to_find, dish_urls_to_find)

    # if dishes_information:
    #     print(f"Successfully processed {len(dishes_information)} dish(es).\n")
    #     # Pretty print the final list of processed dish data
    #     print(json.dumps(dishes_information, indent=2))
    # else:
    #     print("Could not retrieve information for any of the specified dishes.")

# data = []
# with open(config['kb_path'], 'r', encoding='utf-8') as f:
#     for line in f:
#         data.append(json.loads(line))

# # Save data[0] to a separate file
# with open('first_record.json', 'w', encoding='utf-8') as out_f:
#     json.dump(data[0], out_f, ensure_ascii=False, indent=2)


# model = KBQA.from_pretrained(config)

# question = 'What are birthday recipes that do not consist of ingredient white sugar and are low fat, and have white bread, and do not have red currant jelly, gruyere, and contain calories from saturated fat with desired range 10.0 % to 35.0 %?'

# question = 'What are breakfast recipes that consist eggs, milk and meat? and does not have bread'
# question_type = 'constraint'

# topic_entities = ['http://idea.rpi.edu/heals/kb/tag/breakfast']

# multi_tag_type = 'none'

# entities = [['breakfast', 'tag']]

# persona = {'ingredient_likes': [], 'ingredient_dislikes': []}

# guideline = {}

# explicit_nutrition = []

# similar_recipes = {}

# answer_list, answer_id_list, rel_path_list, query_attn, err_code, err_msg = model.answer(question, question_type, topic_entities,
#                                                                                         entities, multi_tag_type=multi_tag_type,
#                                                                                         persona=persona, guideline=guideline,
#                                                                                         explicit_nutrition=explicit_nutrition,
#                                                                                         similar_recipes=similar_recipes)
# print('number of answers:', len(answer_list))
# print('Answer List:', answer_list)
# print('Answer ID List:', answer_id_list)


# # data = json.load(open(config['dish_info_file'], 'r', encoding='utf-8'))
# # print(data.get('Amazing Muffin Cups', None))