import spacy
from typing import Dict, List, Set

class QueryProcessor:
    """
    A class to process natural language food queries. It extracts topics and
    ingredients, then merges them with a user's saved preferences and request data.
    """

    def __init__(self):
        """
        Initializes the QueryProcessor by loading the spaCy NLP model.
        """
        try:
            self.nlp = spacy.load("en_core_web_sm")
            print("QueryProcessor initialized: spaCy model loaded.")
        except OSError:
            print("\n[ERROR] spaCy model 'en_core_web_sm' not found.")
            print("Please run: python -m spacy download en_core_web_sm\n")
            raise

    def _get_full_noun_phrase(self, token: spacy.tokens.Token) -> str:
        """
        Recursively finds the full noun phrase for a given token,
        including compounds, adjectives, and other modifiers.
        """
        parts = [child.text for child in token.lefts if child.dep_ in ('compound', 'amod', 'nummod')]
        parts.append(token.text)
        return " ".join(parts)

    def _clean_topic_phrase(self, phrase: str) -> str:
        """Removes generic trailing words like "recipes" or "dishes"."""
        generic_words = ["recipes", "dishes", "recipe", "dish"]
        # Split phrase to handle multi-word topics correctly
        words = phrase.split()
        if words and words[-1].lower() in generic_words:
            # Join all but the last word
            return " ".join(words[:-1]).strip()
        return phrase.strip()

    def _extract_entities_from_question(self, question_text: str) -> Dict[str, List[str]]:
        """
        Uses dependency parsing to extract topics, liked ingredients, and
        disliked ingredients from a question.
        """
        doc = self.nlp(question_text)
        
        topics = set()
        likes = set()
        dislikes = set()

        POSITIVE_PREPS = {"with", "including"}
        NEGATIVE_PREPS = {"without", "excluding", "no", "not"}
        NEGATION_DEPS = {"neg"}
        
        # --- CORRECTED TOPIC EXTRACTION LOGIC ---
        # This new logic is more robust and checks multiple dependency patterns.
        
        # Pattern 1: Look for direct objects or subjects of the root verb.
        root = [token for token in doc if token.head == token][0]
        topic_candidates = [child for child in root.children if child.dep_ in ('dobj', 'nsubj', 'attr')]
        
        # Pattern 2: Fallback for questions like "What about [topic]?"
        if not topic_candidates:
            topic_candidates = [token for token in doc if token.dep_ == 'pobj']

        for topic_head in topic_candidates:
            phrase = self._get_full_noun_phrase(topic_head)
            cleaned_phrase = self._clean_topic_phrase(phrase)
            if cleaned_phrase:
                topics.add(cleaned_phrase)
            # Find conjuncts (e.g., "turkish or beef-ribs")
            for conjunct in topic_head.conjuncts:
                conj_phrase = self._get_full_noun_phrase(conjunct)
                cleaned_conj = self._clean_topic_phrase(conj_phrase)
                if cleaned_conj:
                    topics.add(cleaned_conj)

        # --- Ingredient Extraction (Likes and Dislikes) ---
        for token in doc:
            # Handle phrases like "without onions" or "with garlic"
            if token.text.lower() in POSITIVE_PREPS or token.text.lower() in NEGATIVE_PREPS:
                for child in token.children:
                    if child.dep_ == "pobj":
                        ingredient = self._get_full_noun_phrase(child)
                        target_set = likes if token.text.lower() in POSITIVE_PREPS else dislikes
                        target_set.add(ingredient)
                        for conj in child.conjuncts:
                             target_set.add(self._get_full_noun_phrase(conj))
            
            # Handle phrases like "don't have onions"
            if token.dep_ in NEGATION_DEPS and token.head.pos_ == "VERB":
                verb = token.head
                for child in verb.children:
                    if child.dep_ == "dobj":
                        dislikes.add(self._get_full_noun_phrase(child))

        return {
            "topics": sorted(list(topics)),
            "likes_from_question": sorted(list(likes)),
            "dislikes_from_question": sorted(list(dislikes)),
        }

    def process_query(
        self,
        question_text: str,
        user_prohibited: List[str],
    ) -> Dict[str, List[str]]:
        """
        The main public method to process a query.
        """
        extracted_entities = self._extract_entities_from_question(question_text)
    
        
        saved_dislikes = set(user_prohibited)
        question_dislikes = set(extracted_entities["dislikes_from_question"])
        merged_dislikes = sorted(list(saved_dislikes.union(question_dislikes)))

        return {
            "final_likes": sorted(list(set(extracted_entities["likes_from_question"]))),
            "final_dislikes": merged_dislikes,
        }

# ===================================================================
#                      Example Usage (for testing)
# ===================================================================

if __name__ == "__main__":
    processor = QueryProcessor()
    
    sample_user_preferences = {"likes": ["garlic"], "dislikes": ["cilantro"]}
    
    test_questions = [
        "Can you suggest spicy chicken dishes without onions?",
        "What are some pasta recipes with tomatoes and oregano?",
        "Recommend turkish or beef-ribs recipes.",
        "What about italian food?",
        "What high-fiber dishes can I make without red onions?",
    ]

    print("\n--- Running Example Queries with Corrected Logic ---\n")

    for i, question in enumerate(test_questions):
        print(f"--- Test Case #{i+1} ---")
        print(f"Input Question: \"{question}\"")
        
        processed_data = processor.process_query(question, sample_user_preferences)
        
        print("\n[Processed Output]")
        print(f"  - Topics: {processed_data['final_topics']}")
        print(f"  - Final Likes (Merged): {processed_data['final_likes']}")
        print(f"  - Final Dislikes (Merged): {processed_data['final_dislikes']}")
        print("-" * 50 + "\n")