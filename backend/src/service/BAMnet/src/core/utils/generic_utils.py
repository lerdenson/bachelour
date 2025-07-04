'''
Created on Oct, 2017

@author: hugo

'''
import re, string
import numpy as np
from rapidfuzz import fuzz, process

from .utils import dump_ndarray, tokenize
from service.BAMnet.src.core import config


question_word_list = 'who, when, what, where, how, which, why, whom, whose'.split(', ')

def find_parent(x, tree, conn='<-'):
    root = tree[0][0]
    path = []
    for parent, indicator, child in tree:
        if x == child[0]:
            path.extend([conn, '__{}__'.format(indicator), '-', parent[0]])
            if not parent == root:
                p = find_parent(parent[0], tree, conn)
                path.extend(p)
            return path
    return path

def extract_dep_feature(dep_parser, text, topic_ent, question_word):
    from nltk.corpus import stopwords
    stop_words = set(stopwords.words("english"))

    dep = dep_parser.raw_parse(text).__next__()
    tree = list(dep.triples())
    topic_ent = list(set(tokenize(topic_ent)) - stop_words)
    text = text.split()

    path_len = 1e5
    topic_ent_to_root = []
    for each in topic_ent:
        ret = process.extractOne(each, text, scorer=fuzz.token_sort_ratio)
        if ret[1] < 85:
            continue
        tmp = find_parent(ret[0], tree, '->')
        if len(tmp) > 0 and len(tmp) < path_len:
            topic_ent_to_root = tmp
            path_len = len(tmp)
    question_word_to_root = find_parent(question_word, tree)
    # if len(question_word_to_root) == 0 or len(topic_ent_to_root) == 0:
        # import pdb;pdb.set_trace()
    return question_word_to_root + list(reversed(topic_ent_to_root[:-1]))

def unique(seq):
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

re_art = re.compile(r'\b(a|an|the)\b')
re_punc = re.compile(r'[%s]' % re.escape(string.punctuation))

def normalize_answer(s):
    """Lower text and remove extra whitespace."""
    def remove_articles(text):
        return re_art.sub(' ', text)

    # def remove_punc(text):
    #     return re_punc.sub(' ', text)  # convert punctuation to spaces

    def white_space_fix(text):
        return ' '.join(text.split())

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(lower(s)))

def load_embeddings(vocab_dict, emb_file, out_path, scale=0.08, seed=123, dtype=np.float32):
    np.random.seed(seed)

    embeddings = None
    hit_words = set()
    vocab_size = len(vocab_dict)
    with open(emb_file, 'rb') as f:
        for line in f:
            line = line.split()
            word = line[0].decode('utf-8')
            idx = vocab_dict.get(word.lower(), None)
            if idx is None or idx in hit_words:
                continue

            vec = np.array(line[1:], dtype=dtype)
            if embeddings is None:
                n_dims = len(vec)
                embeddings = np.array(np.random.uniform(low=-scale, high=scale, size=(vocab_size, n_dims)), dtype=dtype)
                embeddings[config.RESERVED_TOKENS['PAD']] = np.zeros(n_dims)
            embeddings[idx] = vec
            hit_words.add(idx)
    print('Pretrained word embeddings hit ratio: {}'.format(len(hit_words) / len(vocab_dict)))
    dump_ndarray(embeddings, out_path)
    return embeddings


def dump_embeddings(vocab_dict, emb_file, out_path, emb_size=300, binary=False, seed=123):
    vocab_emb = get_embeddings(emb_file, vocab_dict, binary)

    vocab_size = len(vocab_dict)
    np.random.seed(seed)
    embeddings = np.random.uniform(-0.08, 0.08, (vocab_size, emb_size))
    for w, idx in vocab_dict.items():
        if w in vocab_emb:
            embeddings[int(idx)] = vocab_emb[w]
    embeddings[0] = 0
    dump_ndarray(embeddings, out_path)
    return embeddings

def get_embeddings(emb_file, vocab, binary=False):
    pt = PreTrainEmbedding(emb_file, binary)
    vocab_embs = {}

    i = 0.
    for each in vocab:
        emb = pt.get_embeddings(each)
        if not emb is None:
            vocab_embs[each] = emb
            i += 1
    print('get_wordemb hit ratio: %s' % (i / len(vocab)))
    return vocab_embs

class PreTrainEmbedding():
    def __init__(self, file, binary=False):
        import gensim
        self.model = gensim.models.KeyedVectors.load_word2vec_format(file, binary=binary)

    def get_embeddings(self, word):
        word_list = [word, word.upper(), word.lower(), word.title(), string.capwords(word, '_')]

        for w in word_list:
            try:
                return self.model[w]
            except KeyError:
                # print('Can not get embedding for ', w)
                continue
        return None

def load_embeddings(word2index, file_path, out_path, scale=0.08, seed=123, dtype=np.float32):
    np.random.seed(seed)
    hit_words = set()
    vocab_size = len(word2index)

    embeddings = None
    with open(file_path, 'rb') as f:
        for line in f:
            line = line.split()
            word = line[0].decode('utf-8')
            idx = word2index.get(word.lower(), None)
            if idx is None or idx in hit_words:
                continue

            vec = np.array(line[1:], dtype=dtype)
            if embeddings is None:
                n_dims = len(vec)
                embeddings = np.array(np.random.uniform(low=-scale, high=scale, size=(vocab_size, n_dims)), dtype=dtype)
                embeddings[0] = np.zeros(n_dims)

            embeddings[idx] = vec
            hit_words.add(idx)
    print('Pretrained word embeddings hit ratio: {}'.format(len(hit_words) / vocab_size))
    dump_ndarray(embeddings, out_path)
    print('saved pretrained word embeddings to {}'.format(out_path))
