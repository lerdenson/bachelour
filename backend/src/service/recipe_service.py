import logging
from typing import Dict, List, Tuple, Any

import schemas

from service.BAMnet.src.core.kbqa import KBQA
from repository import models
from service.query_processor import QueryProcessor
from service.recipe_data_extractor import RecipeDataExtractor  # Import the new class

logger = logging.getLogger(__name__)
tag_url_prefix = 'http://idea.rpi.edu/heals/kb/tag/'

class RecipeService:
    def __init__(self, config: Dict):
        logger.info("Initializing RecipeService...")
        self.model = KBQA.from_pretrained(config)
        self.query_processor = QueryProcessor()
        
        # Initialize the new RecipeDataExtractor
        self.recipe_extractor = RecipeDataExtractor(kg_path=config.get("kb_path"))

        logger.info("RecipeService initialized successfully.")

    def find_recipes(
        self,
        request: schemas.QuestionRequest,
        user: models.User
    ) -> List[Dict[str, Any]]:
        logger.info(f"Finding recipes for user: {user.email} with question: '{request.question}'")

        # Use QueryProcessor to get final merged topics and preferences
        processed_query = self.query_processor.process_query(
            question_text=request.question,
            user_prohibited=user.prohibited_ingredients or [],
        )
        logger.debug(f"Processed Query Entities: {processed_query}")
        topics = request.tags
        if len(topics) == 0:
            topics.append('georgian')
        else:
            for topic in topics:
                topic.replace(' ', '-')

        entities = [[tag, 'tag'] for tag in topics]

        tags = []
        if not request.tags:
            logger.warning("No tags provided in the request. Model performance may be affected.")
        for topic in topics:
            tags.append(tag_url_prefix + topic)

        final_likes = processed_query['final_likes']
        final_dislikes = processed_query['final_dislikes']

        # Construct the 'persona' object for the ML model
        model_persona = {
            'ingredient_likes': final_likes,
            'ingredient_dislikes': final_dislikes,
        }
        constrained_entities = {}
        if final_likes:
            constrained_entities['1'] = final_likes
        if final_dislikes:
            constrained_entities['2'] = final_dislikes
        
        if constrained_entities:
            model_persona['constrained_entities'] = constrained_entities

        logger.info(f"Final topics sent to model: {tags}")
        logger.info(f"Constructed final persona for model: {model_persona}")
        
        # Call the KBQA model to get a list of recipe URLs 
        _, answer_id_list, _, _, err_code, err_msg = self.model.answer(
            question=request.question,
            question_type='constraint',
            topic_entities=tags,
            entities=entities,
            persona=model_persona,
            guideline={},
            explicit_nutrition=[],
            similar_recipes={},
        )

        # Step 4: Handle the response from the model
        if err_code != 0:
            logger.error(f"KBQA model returned an error: {err_msg}")
            raise ValueError(err_msg)

        logger.info(f"Model returned {len(answer_id_list)} recipe URLs.")

        # Step 5: Use the RecipeDataExtractor to get and format the recipe data
        if not answer_id_list or not tags:
            logger.info("No recipe IDs returned or no tags provided, returning empty list.")
            return []

        # We use the first tag as the entry point to find the dishes.
        primary_tag_url = tags[0]
        recipe_data = self.recipe_extractor.get_dishes_by_urls(
            tag_url=primary_tag_url,
            dish_urls=answer_id_list
        )

        logger.info(f"Successfully formatted data for {len(recipe_data)} recipes.")
        return recipe_data

