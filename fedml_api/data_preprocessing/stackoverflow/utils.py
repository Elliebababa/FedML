import logging

import numpy as np
import collections

word_count_file_path = '../../../data/stackoverflow/datasets/stackoverflow.word_count'
word_dict = None
word_list = None
_pad = '<pad>'
_bos = '<bos>'
_eos = '<eos>'

'''
This code follows the steps of preprocessing in tff stackoverflow dataset: 
https://github.com/tensorflow/federated/blob/786d0a0c51099dc9ee6f06b9344e4bd311ab52bd/tensorflow_federated/python/research/utils/datasets/stackoverflow_dataset.py
'''

def get_most_frequent_words(vocab_size = 100):
    frequent_words = []
    with open(word_count_file_path) as f:
        for line in f:
            word, count = line.split()
            frequent_words.append(word)
            if len(frequent_words) == vocab_size:
                break
    return frequent_words

def get_word_dict():
    global word_dict
    if word_dict == None:
        frequent_words = get_most_frequent_words()
        words = [_pad] + frequent_words + [_bos] + [_eos]
        word_dict = collections.OrderedDict()
        for i, w in enumerate(words):
            word_dict[w] = i
    return word_dict

def get_word_list():
    global word_list
    if word_list == None:
        word_dict = get_word_dict()
        word_list = list(word_dict.keys())
    return word_list

def id_to_word(idx):
    return get_word_list[idx]

def word_to_id(word, num_oov_buckets = 1):
    word_dict = get_word_dict()
    if word in word_dict:
        return word_dict[word]
    else:
        return hash(word)%num_oov_buckets + len(word_dict)
    
def preprocess(sentences, max_seq_len = 120):
    
    truncated_sentences = [sentence.split(' ')[:max_seq_len] for sentence in sentences]
    
    def to_ids(sentence, num_oov_buckets = 1):
        '''
        map list of sentence to list of [idx..] and pad to max_seq_len + 1
        Args:
            num_oov_buckets : The number of out of vocabulary buckets.
            max_seq_len: Integer determining shape of padded batches.
        '''
        tokens = [word_to_id(token) for token in sentence]
        if len(tokens) < max_seq_len:
            tokens = tokens + [word_dict[_eos]]
        tokens = [word_dict[_bos]] + tokens
        if len(tokens) < max_seq_len + 1:
            tokens += [0] * (max_seq_len + 1 - len(tokens))
        return tokens
    
    return [to_ids(sentence) for sentence in truncated_sentences]
    
def split(dataset):
    ds = np.array(dataset)
    x = ds[:,:-1]
    y = ds[:,1:]
    return x, y

if __name__ == "__main__":
    print(preprocess(['this will output :',
       'the simplest way i know how to do that is to move the file , delete the file using svn , and then move the file back .',]))