'''
Created on Sep, 2017

@author: hugo

'''
import os
import timeit
import numpy as np

import torch
from torch import optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.nn import MultiLabelMarginLoss
import torch.backends.cudnn as cudnn

from .modules import BAMnet
from .utils import to_cuda, next_batch
from ..utils.utils import load_ndarray
from ..utils.generic_utils import unique
from ..utils.metrics import *
from .. import config


CTX_BOW_INDEX = -5
def get_text_overlap(raw_query, query_mentions, ctx_ent_names, vocab2id, ctx_stops, query):
    def longest_common_substring(s1, s2):
       m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
       longest, x_longest = 0, 0
       for x in range(1, 1 + len(s1)):
           for y in range(1, 1 + len(s2)):
               if s1[x - 1] == s2[y - 1]:
                   m[x][y] = m[x - 1][y - 1] + 1
                   if m[x][y] > longest:
                       longest = m[x][y]
                       x_longest = x
               else:
                   m[x][y] = 0
       return s1[x_longest - longest: x_longest]

    sub_seq = longest_common_substring(raw_query, ctx_ent_names)
    if len(set(sub_seq) - ctx_stops) == 0:
        return []

    men_type = None
    for men, type_ in query_mentions:
        if type_.lower() in config.constraint_mention_types:
            if '_'.join(sub_seq) in '_'.join(men):
                men_type = '__{}__'.format(type_.lower())
                break

    if men_type:
        return [vocab2id[men_type] if men_type in vocab2id else config.RESERVED_TOKENS['UNK']]
    else:
        return [vocab2id[x] if x in vocab2id else config.RESERVED_TOKENS['UNK'] for x in sub_seq]


def string_search(src, tgt):
    indices = [i for i, x in enumerate(src) if x == tgt[0]]
    hit = False
    for i in indices:
        if src[i: i + len(tgt)] == tgt:
            start_idx = i
            end_idx = i + len(tgt)
            hit = True
            break
    return (start_idx, end_idx) if hit else (-1, -1)


class BAMnetAgent(object):
    """ Bidirectional attentive memory network agent.
    """
    def __init__(self, opt, ctx_stops, vocab2id):
        self.ctx_stops = ctx_stops
        self.vocab2id = vocab2id
        opt['cuda'] = not opt['no_cuda'] and torch.cuda.is_available()
        if opt['cuda']:
            print('[ Using CUDA ]')
            torch.cuda.set_device(opt['gpu'])
            # It enables benchmark mode in cudnn, which
            # leads to faster runtime when the input sizes do not vary.
            cudnn.benchmark = True

        self.opt = opt
        if self.opt['pre_word2vec'] and os.path.exists(self.opt['pre_word2vec']):
            pre_w2v = load_ndarray(self.opt['pre_word2vec'])
        else:
            pre_w2v = None

        self.model = BAMnet(opt['vocab_size'], opt['vocab_embed_size'], \
                opt['o_embed_size'], opt['hidden_size'], \
                opt['num_ent_types'], opt['num_relations'], \
                opt['num_query_words'], \
                constraint_mark_emb=opt.get('constraint_mark_emb'), \
                word_emb_dropout=opt['word_emb_dropout'], \
                que_enc_dropout=opt['que_enc_dropout'], \
                ans_enc_dropout=opt['ans_enc_dropout'], \
                pre_w2v=pre_w2v, \
                num_hops=opt['num_hops'], \
                att=opt['attention'], \
                fix_word_emb=opt.get('fix_word_emb', False), \
                use_entity_name=opt.get('use_entity_name', False), \
                use_cuda=opt['cuda'])
        if opt['cuda']:
            self.model.cuda()

        # MultiLabelMarginLoss
        # For each sample in the mini-batch:
        # loss(x, y) = sum_ij(max(0, 1 - (x[y[j]] - x[i]))) / x.size(0)
        self.loss_fn = MultiLabelMarginLoss()

        optim_params = [p for p in self.model.parameters() if p.requires_grad]
        self.optimizer = optim.Adam(optim_params, lr=opt['learning_rate'])
        self.scheduler = ReduceLROnPlateau(self.optimizer, mode='max', \
                    patience=self.opt['valid_patience'] // 3)

        if opt.get('model_file'):
            if os.path.isfile(opt['model_file']):
                print('Loading existing model parameters from ' + opt['model_file'])
                self.load(opt['model_file'])
            else:
                os.makedirs(os.path.dirname(opt['model_file']), exist_ok=True)

        super(BAMnetAgent, self).__init__()

    def train(self, train_X, train_y, valid_X, valid_y, valid_cand_labels, valid_gold_ans_labels, seed=1234):
        print('Training size: {}, Validation size: {}'.format(len(train_y), len(valid_y)))
        random1 = np.random.RandomState(seed)
        random2 = np.random.RandomState(seed)
        random3 = np.random.RandomState(seed)
        random4 = np.random.RandomState(seed)
        random5 = np.random.RandomState(seed)
        random6 = np.random.RandomState(seed)
        random7 = np.random.RandomState(seed)
        random8 = np.random.RandomState(seed)
        memories, queries, query_words, raw_queries, query_mentions, query_marks, query_lengths = train_X
        gold_ans_inds = train_y

        valid_memories, valid_queries, valid_query_words, valid_raw_queries, valid_query_mentions, valid_query_marks, valid_query_lengths = valid_X
        valid_gold_ans_inds = valid_y

        n_incr_error = 0  # nb. of consecutive increase in error
        best_loss = float("inf")
        best_f1 = 0
        num_batches = len(queries) // self.opt['batch_size'] + (len(queries) % self.opt['batch_size'] != 0)
        num_valid_batches = len(valid_queries) // self.opt['batch_size'] + (len(valid_queries) % self.opt['batch_size'] != 0)
        for epoch in range(1, self.opt['num_epochs'] + 1):
            start = timeit.default_timer()
            n_incr_error += 1
            random1.shuffle(memories)
            random2.shuffle(queries)
            random3.shuffle(query_words)
            random4.shuffle(raw_queries)
            random5.shuffle(query_mentions)
            random6.shuffle(query_marks)
            random7.shuffle(query_lengths)
            random8.shuffle(gold_ans_inds)

            train_gen = next_batch(memories, queries, query_words, raw_queries, query_mentions, query_marks, query_lengths, gold_ans_inds, self.opt['batch_size'])
            self.optimizer.zero_grad()
            train_loss = 0
            for step, (batch_xs, batch_ys) in enumerate(train_gen):
                train_loss += self.train_step(batch_xs, batch_ys, step) / num_batches

            valid_gen = next_batch(valid_memories, valid_queries, valid_query_words, valid_raw_queries, valid_query_mentions, valid_query_marks, valid_query_lengths, valid_gold_ans_inds, self.opt['batch_size'])
            valid_loss = 0
            for step, (batch_valid_xs, batch_valid_ys) in enumerate(valid_gen):
                valid_loss += self.train_step(batch_valid_xs, batch_valid_ys, step, is_training=False) / num_valid_batches

            pred, _ = self.predict(valid_X, valid_cand_labels, batch_size=1, margin=self.opt['test_margin'][0], silence=True)
            predictions = [unique([valid_cand_labels[qid][x[0]] for x in each]) for qid, each in enumerate(pred)]
            valid_f1 = calc_avg_f1(valid_gold_ans_labels, predictions, verbose=False)[-1]
            print('Epoch {}/{}: Runtime: {}s, Train loss: {:.4}, valid loss: {:.4}, valid F1: {:.4}'.format(epoch, self.opt['num_epochs'], \
                                                    int(timeit.default_timer() - start), train_loss, valid_loss, valid_f1))

            self.scheduler.step(valid_f1)
            if valid_f1 > best_f1:
                best_f1 = valid_f1
                n_incr_error = 0
                self.save()

            if n_incr_error >= self.opt['valid_patience']:
                print('Early stopping occured. Optimization Finished!')
                print('Best F1: {}'.format(best_f1))
                break

    def predict(self, xs, cand_labels, batch_size=32, margin=1, ys=None, verbose=False, silence=False):
        '''Prediction scores are returned in the verbose mode.
        '''
        if not silence:
            print('Testing size: {}'.format(len(cand_labels)))
        memories, queries, query_words, raw_queries, query_mentions, query_marks, query_lengths = xs
        gen = next_batch(memories, queries, query_words, raw_queries, query_mentions, query_marks, query_lengths, cand_labels, batch_size)
        predictions = []
        query_attn = []
        for batch_xs, batch_cands in gen:
            batch_pred, batch_query_attn = self.predict_step(batch_xs, batch_cands, margin, verbose=verbose)
            # batch_pred = self.predict_step_agile(batch_xs, batch_cands, margin, topn=300, verbose=verbose)
            predictions.extend(batch_pred)
            query_attn.extend(batch_query_attn)
        return predictions, query_attn

    def train_step(self, xs, ys, step, is_training=True):
        # Sets the module in training mode.
        # This has any effect only on modules such as Dropout or BatchNorm.
        self.model.train(mode=is_training)
        with torch.set_grad_enabled(is_training):
            # Organize inputs for network
            selected_memories, new_ys, ctx_mask = self.dynamic_ctx_negative_sampling(xs[0], ys, self.opt['mem_size'], \
                                    self.opt['ans_ctx_entity_bow_size'], xs[3], xs[4], xs[1], xs[5])
            selected_memories = [to_cuda(torch.LongTensor(np.array(x)), self.opt['cuda']) for x in zip(*selected_memories)]
            ctx_mask = to_cuda(ctx_mask, self.opt['cuda'])
            queries = to_cuda(torch.LongTensor(xs[1]), self.opt['cuda'])
            query_words = to_cuda(torch.LongTensor(xs[2]), self.opt['cuda'])
            query_marks = to_cuda(torch.LongTensor(xs[5]), self.opt['cuda'])
            query_lengths = to_cuda(torch.LongTensor(xs[6]), self.opt['cuda'])
            mem_hop_scores, _ = self.model(selected_memories, queries, query_marks, query_lengths, query_words, ctx_mask=None)
            # Set margin
            new_ys, mask_ys = self.pack_gold_ans(new_ys, mem_hop_scores[-1].size(1), placeholder=-1)

            loss = 0
            for _, s in enumerate(mem_hop_scores):
                s = self.set_loss_margin(s, mask_ys, self.opt['margin'])
                loss += self.loss_fn(s, new_ys)
            loss /= len(mem_hop_scores)
            loss_value = loss.item()

            if is_training:
                # Accumulate gradients
                loss = loss / self.opt['grad_accumulated_steps'] # Normalize our loss (if averaged)
                # Run backward
                loss.backward()

                if (step + 1) % self.opt['grad_accumulated_steps'] == 0: # Wait for several backward steps
                    # Update parameters
                    self.optimizer.step()
                    self.optimizer.zero_grad()
            return loss_value

    def predict_step(self, xs, cand_labels, margin, verbose=False):
        self.model.train(mode=False)
        with torch.set_grad_enabled(False):
            # Organize inputs for network
            memories, ctx_mask = self.pad_ctx_memory(xs[0], self.opt['ans_ctx_entity_bow_size'], xs[3], xs[4], xs[1], xs[5])
            memories = [to_cuda(torch.LongTensor(np.array(x)), self.opt['cuda']) for x in zip(*memories)]
            ctx_mask = to_cuda(ctx_mask, self.opt['cuda'])
            queries = to_cuda(torch.LongTensor(xs[1]), self.opt['cuda'])
            query_words = to_cuda(torch.LongTensor(xs[2]), self.opt['cuda'])
            query_marks = to_cuda(torch.LongTensor(xs[5]), self.opt['cuda'])
            query_lengths = to_cuda(torch.LongTensor(xs[6]), self.opt['cuda'])
            mem_hop_scores, query_attn = self.model(memories, queries, query_marks, query_lengths, query_words, ctx_mask=None)

            predictions = self.ranked_predictions(cand_labels, mem_hop_scores[-1].data, margin)
            return predictions, query_attn.cpu().numpy().tolist()

    # def predict_step_agile(self, xs, cand_labels, margin, topn=300, verbose=False):
    #     self.model.train(mode=False)
    #     with torch.set_grad_enabled(False):
    #         # Organize inputs for network
    #         # Step 1) Pre-select topn candidates
    #         memories, ctx_mask = self.pad_ctx_memory(xs[0], self.opt['ans_ctx_entity_bow_size'], xs[3], xs[4], xs[1])
    #         memories = [to_cuda(torch.LongTensor(np.array(x)), self.opt['cuda']) for x in zip(*memories)]
    #         ctx_mask = to_cuda(ctx_mask, self.opt['cuda'])
    #         queries = to_cuda(torch.LongTensor(xs[1]), self.opt['cuda'])
    #         query_words = to_cuda(torch.LongTensor(xs[2]), self.opt['cuda'])
    #         query_lengths = to_cuda(torch.LongTensor(xs[5]), self.opt['cuda'])
    #         pre_score = self.model.premature_score(memories, queries, query_lengths, ctx_mask=ctx_mask).data
    #         _, sorted_inds = pre_score.sort(descending=True, dim=1)
    #         selected_inds = sorted_inds[:, :topn]

    #         for i in range(len(memories)):
    #             trank = len(memories[i].size())
    #             if trank == 1:
    #                 memories[i] = torch.clamp(memories[i], max=topn)
    #             elif trank == 2:
    #                 memories[i] = memories[i].gather(1, selected_inds)
    #             elif trank == 3:
    #                 memories[i] = memories[i].gather(1, selected_inds.unsqueeze(-1).repeat(1, 1, memories[i].size(-1)))
    #             elif trank == 4:
    #                 memories[i] = memories[i].gather(1, selected_inds.unsqueeze(-1).unsqueeze(-1).repeat(1, 1, memories[i].size(-2), memories[i].size(-1)))
    #             else:
    #                 raise RuntimeError('Unexpected tensor rank: {}'.format(trank))
    #         ctx_mask = ctx_mask.gather(1, selected_inds)
    #         selected_cand_labels = [[x[int(j)] for j in selected_inds[i] if int(j) < len(x)] for i, x in enumerate(cand_labels)]

    #         # Step 2) Run the full model on the selected topn candidates
    #         mem_hop_scores = self.model(memories, queries, query_lengths, query_words, ctx_mask=None)
    #         predictions = self.ranked_predictions(selected_cand_labels, mem_hop_scores[-1].data, margin)
    #         return predictions

    def dynamic_ctx_negative_sampling(self, memories, ys, mem_size, ctx_bow_size, raw_queries, query_mentions, queries, query_marks):
        # Randomly select negative samples from the candidiate answer set
        ctx_bow_size = max(min(max(map(len, (a for x in list(zip(*memories))[CTX_BOW_INDEX] for y in x for a in y)), default=0), ctx_bow_size), 1)

        selected_memories = []
        new_ys = []
        ctx_mask = []
        for i in range(len(ys)):
            n = len(memories[i][0]) - 1 # The last element is a dummy candidate
            num_gold = len(ys[i]) if mem_size > len(ys[i]) else \
                    (mem_size - min(mem_size // 2, n - len(ys[i]))) # Max possible (pos, neg) pairs
            selected_gold_inds = np.random.choice(ys[i], num_gold, replace=False).tolist() if len(ys[i]) > 0 else []
            if n > len(ys[i]):
                p = np.ones(n)
                p[ys[i]] = 0
                p = p / np.sum(p)
                selected_inds = np.random.choice(n, min(mem_size, n) - num_gold, replace=False, p=p).tolist()
            else:
                selected_inds = []
            augmented_selected_inds = selected_gold_inds + selected_inds + [-1] * max(mem_size - n, 0)
            xx = [min(mem_size, n)] + [np.array(x)[augmented_selected_inds] for x in memories[i][:CTX_BOW_INDEX]]

            ctx_bow = []
            ctx_bow_len = []
            ctx_marks = []
            ctx_num = []
            tmp_ctx_mask = np.zeros(mem_size)
            for _, idx in enumerate(augmented_selected_inds):
                tmp_ctx = []
                tmp_ctx_len = []
                tmp_ctx_marks = []
                for ctx_ent_names in memories[i][CTX_BOW_INDEX][idx]:
                    sub_seq = get_text_overlap(raw_queries[i], query_mentions[i], ctx_ent_names, self.vocab2id, self.ctx_stops, queries[i])
                    if len(sub_seq) > 0:
                        start_idx, end_idx = string_search(queries[i], sub_seq)
                        tmp_ctx_mask[_] = 1
                        tmp_ctx.append(sub_seq[:ctx_bow_size] + [config.RESERVED_TOKENS['PAD']] * max(0, ctx_bow_size - len(sub_seq)))
                        tmp_ctx_len.append(max(min(ctx_bow_size, len(sub_seq)), 1))
                        mark_vec = query_marks[i][start_idx: end_idx].tolist()
                        mark_vec = mark_vec[:ctx_bow_size] + [0] * max(0, ctx_bow_size - len(mark_vec))
                        tmp_ctx_marks.append(mark_vec)

                ctx_bow.append(tmp_ctx)
                ctx_bow_len.append(tmp_ctx_len)
                ctx_num.append(len(tmp_ctx))
                ctx_marks.append(tmp_ctx_marks)

            xx += [ctx_bow, ctx_marks, ctx_bow_len, ctx_num]
            xx += [np.array(x)[augmented_selected_inds] for x in memories[i][CTX_BOW_INDEX+1:]]
            selected_memories.append(xx)
            new_ys.append(list(range(num_gold)))
            ctx_mask.append(tmp_ctx_mask)

        max_ctx_num = max(max([y for x in selected_memories for y in x[CTX_BOW_INDEX]]), 1)
        for i in range(len(selected_memories)): # Example
            for j in range(len(selected_memories[i][-1])): # Cand
                count = selected_memories[i][CTX_BOW_INDEX][j]
                if count < max_ctx_num:
                    selected_memories[i][CTX_BOW_INDEX - 3][j] += [[config.RESERVED_TOKENS['PAD']] * ctx_bow_size] * (max_ctx_num - count)
                    selected_memories[i][CTX_BOW_INDEX - 2][j] += [[0] * ctx_bow_size] * (max_ctx_num - count)
                    selected_memories[i][CTX_BOW_INDEX - 1][j] += [1] * (max_ctx_num - count)
        return selected_memories, new_ys, torch.Tensor(np.array(ctx_mask))

    def pad_ctx_memory(self, memories, ctx_bow_size, raw_queries, query_mentions, queries, query_marks):
        cand_ans_size = max(max(map(len, list(zip(*memories))[0]), default=0) - 1, 1) # The last element is a dummy candidate
        ctx_bow_size = max(min(max(map(len, (a for x in list(zip(*memories))[CTX_BOW_INDEX] for y in x for a in y)), default=0), ctx_bow_size), 1)

        pad_memories = []
        ctx_mask = []
        for i in range(len(memories)):
            n = len(memories[i][0]) - 1 # The last element is a dummy candidate
            augmented_inds = list(range(n)) + [-1] * (cand_ans_size - n)
            xx = [n] + [np.array(x)[augmented_inds] for x in memories[i][:CTX_BOW_INDEX]]

            ctx_bow = []
            ctx_bow_len = []
            ctx_marks = []
            ctx_num = []
            tmp_ctx_mask = np.zeros(cand_ans_size)
            for _, idx in enumerate(augmented_inds):
                tmp_ctx = []
                tmp_ctx_len = []
                tmp_ctx_marks = []
                for ctx_ent_names in memories[i][CTX_BOW_INDEX][idx]:
                    sub_seq = get_text_overlap(raw_queries[i], query_mentions[i], ctx_ent_names, self.vocab2id, self.ctx_stops, queries[i])
                    if len(sub_seq) > 0:
                        start_idx, end_idx = string_search(queries[i], sub_seq)
                        tmp_ctx_mask[_] = 1
                        tmp_ctx.append(sub_seq[:ctx_bow_size] + [config.RESERVED_TOKENS['PAD']] * max(0, ctx_bow_size - len(sub_seq)))
                        tmp_ctx_len.append(max(min(ctx_bow_size, len(sub_seq)), 1))
                        mark_vec = query_marks[i][start_idx: end_idx].tolist()
                        mark_vec = mark_vec[:ctx_bow_size] + [0] * max(0, ctx_bow_size - len(mark_vec))
                        tmp_ctx_marks.append(mark_vec)
                ctx_bow.append(tmp_ctx)
                ctx_bow_len.append(tmp_ctx_len)
                ctx_marks.append(tmp_ctx_marks)
                ctx_num.append(len(tmp_ctx))

            xx += [ctx_bow, ctx_marks, ctx_bow_len, ctx_num]
            xx += [np.array(x)[augmented_inds] for x in memories[i][CTX_BOW_INDEX+1:]]
            pad_memories.append(xx)
            ctx_mask.append(tmp_ctx_mask)

        max_ctx_num = max(max([y for x in pad_memories for y in x[CTX_BOW_INDEX]]), 1)
        for i in range(len(pad_memories)): # Example
            for j in range(len(pad_memories[i][-1])): # Cand
                count = pad_memories[i][CTX_BOW_INDEX][j]
                if count < max_ctx_num:
                    pad_memories[i][CTX_BOW_INDEX - 3][j] += [[config.RESERVED_TOKENS['PAD']] * ctx_bow_size] * (max_ctx_num - count)
                    pad_memories[i][CTX_BOW_INDEX - 2][j] += [[0] * ctx_bow_size] * (max_ctx_num - count)
                    pad_memories[i][CTX_BOW_INDEX - 1][j] += [1] * (max_ctx_num - count)
        return pad_memories, torch.Tensor(np.array(ctx_mask))

    def pack_gold_ans(self, x, N, placeholder=-1):
        y = np.ones((len(x), N), dtype='int64') * placeholder
        mask = np.zeros((len(x), N))
        for i in range(len(x)):
            y[i, :len(x[i])] = x[i]
            mask[i, :len(x[i])] = 1
        return to_cuda(torch.LongTensor(y), self.opt['cuda']), to_cuda(torch.Tensor(mask), self.opt['cuda'])

    def set_loss_margin(self, scores, gold_mask, margin):
        """Since the pytorch built-in MultiLabelMarginLoss fixes the margin as 1.
        We simply work around this annoying feature by *modifying* the golden scores.
        E.g., if we want margin as 3, we decrease each golden score by 3 - 1 before
        feeding it to the built-in loss.
        """
        new_scores = scores - (margin - 1) * gold_mask
        return new_scores

    def ranked_predictions(self, cand_labels, scores, margin):
        _, sorted_inds = scores.sort(descending=True, dim=1)
        return [[(j, scores[i][j]) for j in r if scores[i][j] + margin >= scores[i][r[0]] \
                and cand_labels[i][j] != 'UNK'] \
                if len(cand_labels[i]) > 0 and scores[i][r[0]] > -1e4 else [] \
                for i, r in enumerate(sorted_inds)] # Very large negative ones are dummy candidates

    def save(self, path=None):
        path = self.opt.get('model_file', None) if path is None else path

        if path:
            checkpoint = {}
            checkpoint['bamnet'] = self.model.state_dict()
            checkpoint['bamnet_optim'] = self.optimizer.state_dict()
            with open(path, 'wb') as write:
                torch.save(checkpoint, write)
                print('Saved model to {}'.format(path))

    def load(self, path):
        with open(path, 'rb') as read:
            checkpoint = torch.load(read, map_location=lambda storage, loc: storage)
        self.model.load_state_dict(checkpoint['bamnet'])
        self.optimizer.load_state_dict(checkpoint['bamnet_optim'])
