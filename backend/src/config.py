import os

# ===================================================================
#                      Path Configuration
# ===================================================================

# This section creates robust, absolute paths to your data and run directories.
# It assumes this 'config.py' file is located at: /path/to/BAMnet/src/core/
# It calculates the project's root directory and builds all other paths from there.

# Get the directory of the current file (/.../BAMnet/src/core)
_current_dir = os.path.dirname(__file__)

# Calculate the project's root directory by going up two levels
PROJECT_ROOT = os.path.abspath(os.path.join(_current_dir, './service/BAMnet'))

# Define data and runs directories based on the project root
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
RUNS_DIR = os.path.join(PROJECT_ROOT, 'runs')

# ===================================================================
#                   Main Configuration Dictionary
# ===================================================================

config = {
    'name': 'kbqa',

    # --- File Paths (now absolute and robust) ---
    'data_dir': os.path.join(DATA_DIR, 'kbqa'),
    'kb_path': os.path.join(DATA_DIR, 'recipe_kg', 'recipe_kg.json'),
    'train_data': 'train_vec.json',  # These are relative to 'data_dir'
    'valid_data': 'valid_vec.json',
    'test_data': 'test_vec.json',
    'test_raw_data': 'test_qas.json',
    'pre_word2vec': os.path.join(DATA_DIR, 'kbqa', 'glove_pretrained_300d_w2v.npy'),
    
    # Path to the saved model file
    'model_file': os.path.join(RUNS_DIR, 'kbqa', 'pfoodreq_ent_mark_40.model'),

    # --- Vocabulary and Entity Sizes ---
    'vocab_size': 10860,
    'num_ent_types': 7,
    'num_relations': 11,
    'num_query_words': 10,

    # --- Model Hyperparameters ---
    'no_filter_answer_type': False,
    'query_size': 64,
    'ans_type_bow_size': 6,
    'ans_path_bow_size': 6,
    'ans_path_size': 2,
    'ans_ctx_entity_bow_size': 16,
    
    'use_entity_name': False,
    'fix_word_emb': False,
    'constraint_mark_emb': 40,
    'vocab_embed_size': 300,
    'hidden_size': 128,
    'o_embed_size': 128,
    'mem_size': 96,
    'word_emb_dropout': 0.3,
    'que_enc_dropout': 0.3,
    'ans_enc_dropout': 0.2,
    'attention': 'add',
    'num_hops': 1,

    # --- Training Settings ---
    'learning_rate': 0.001,
    'batch_size': 32,
    'grad_accumulated_steps': 1,
    'num_epochs': 100,
    'valid_patience': 10,
    'margin': 1.0, # Converted to float

    # --- Testing Settings ---
    'test_batch_size': 1,
    'test_margin': [0.9], # Note: this is a list with one float element

    # --- Device Settings ---
    'no_cuda': False,
    'gpu': 0,
    
    # --- Other options from kbqa.py that might be needed ---
    'augment_similar_dishs': False,
    'similarity_score_ratio': 0.2,
    
    # These paths are needed by the KBQA class if similarity features are used.
    # We add them here for completeness.
    'dish_info_file': os.path.join(DATA_DIR, 'kbqa', 'dish_info_map.json'),
    'recipe_emb_file': os.path.join(DATA_DIR, 'kbqa', 'recipe_embeddings.npy'),
    'dish_name2id_file': os.path.join(DATA_DIR, 'kbqa', 'dish_name2id.json'),
}

# Define STOPWORDS here if it's used by other modules that import this config.
# This prevents circular dependencies.
STOPWORDS = set()