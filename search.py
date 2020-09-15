#!/usr/bin/env python
# coding: utf-8

# In[1]:


import bisect
import copy
import math
import numpy as np
import operator
import os
from pprint import pprint
import re
from spacy.lang.en.stop_words import STOP_WORDS
from Stemmer import Stemmer
import sys
from time import time
from tqdm import tqdm
import warnings


def get_title_from_one_file(docIDs, title_file_path):
    titles = []
    with open(title_file_path, 'r') as f:
        cntr = 0
        for line in f.readlines():
            if cntr in docIDs:
                line = line.split(' ')
                line = ' '.join(line[:-1])
                titles.append(line)
            cntr += 1
    return titles


# ### Get title of each unique doc id in list of doc ids

# In[6]:


def get_titles(docIDs):
    titles = []
    sorted_ind = sorted(range(len(docIDs)), key=lambda k: docIDs[k])
    docIDs.sort()
    i=0
    while i<len(docIDs):
        doc_id = docIDs[i]
        title_file = doc_id//number_in_one_file + 1
        title_file_path = os.path.join(title_folder_path, str(title_file) + '.txt')
        same_grp_docids = []
        while i < len(docIDs) and docIDs[i]//number_in_one_file + 1 == title_file:
            same_grp_docids.append(docIDs[i]%number_in_one_file)
            i += 1
        titles += get_title_from_one_file(same_grp_docids, title_file_path)
    ret_titles = copy.deepcopy(titles)
    for i in range(len(titles)):
        ret_titles[sorted_ind[i]] = titles[i]
    return ret_titles


# In[7]:


def preprocess_text(text):
    text = text.lower()
    text = re.split(r'[^A-Za-z0-9]+', text)
    for i in range(len(text)):
        text[i] = stemmer.stemWord(text[i])
    text = [w for w in text if not w in STOP_WORDS and len(w) > 1]

    return text


# In[8]:


def get_field_queries(text):
    text = text.split(' ')
    f_qry = {}
    cur_field = ""
    for w in text:
        w = w.split(":")
        if len(w)==1 and cur_field == "":
            return f_qry
        elif len(w)==1:
            f_qry[cur_field] += w[0] + " "
        else:
            cur_field, query = w
            if cur_field not in field_mapping:
                return {}
            cur_field = field_mapping[cur_field]
            if cur_field not in f_qry:
                f_qry[cur_field] = ""
            f_qry[cur_field] += query + " "
    
    for field in f_qry:
        f_qry[field] = preprocess_text(f_qry[field])
    return f_qry


# In[9]:


def preprocess_query(search_query):
    field_terms = {}
    search_terms = []
    search_query = search_query.lower()
    field_keys = list(field_mapping.keys())
    if any(field + ":" in search_query for field in field_keys):
        field_terms = get_field_queries(search_query)
    if not field_terms:
        search_terms = preprocess_text(search_query)
    return search_terms, field_terms


# In[10]:


def get_inverted_list(list_str, fields):
    list_str = list_str.split(' ')
    inv_idx = {}
    idf_score = {}
    for i in range(len(list_str)):
        if i==0:
            continue
        field_data = list_str[i]
        field_data = field_data.split('-')
        cur_field = field_data[0]
        if cur_field not in fields:
            continue
        for occurrence in field_data[1].split(','):
            doc_id, freq = occurrence.split(':')
            if freq[len(freq)-1] == '\n':
                freq = freq[:-1]
            doc_id = int(doc_id)
            freq = int(freq)
            if cur_field not in inv_idx:
                inv_idx[cur_field] = []
            inv_idx[cur_field].append([doc_id, freq])
        idf_score[cur_field] = math.log(total_documents/len(inv_idx[cur_field]))
    for field in inv_idx:
        for i in range(len(inv_idx[field])):
            doc_id = inv_idx[field][i][0]
            freq = inv_idx[field][i][1]
            tf_score = math.log(freq) 
            inv_idx[field][i][1] = tf_score * idf_score[field]
    return inv_idx


# In[11]:


def get_inverted_list_of_word(word, fields):
    idx = bisect.bisect_right(secondary_index_words, word)
    if idx==0:
        return {}
    with open(os.path.join(inv_idx_folder_path, str(idx) + '.txt'), 'r') as f:
        line = f.readline()
        while line and line.split(' ')[0] != word:
            line = f.readline()
        if line:
            return get_inverted_list(line, fields)
        else:
            return {}


# In[12]:


def join_docs(doc1, doc2, idx):
    new_doc = [doc1[0], doc1[1]+doc2[1]]
    tmp = []
    for i in range(len(doc1[2])):
        if i==idx:
            tmp.append(doc1[2][i]+1)
        else:
            tmp.append(doc1[2][i])
    new_doc.append(tmp)
    return new_doc


# In[13]:


def merge_lists(cur_doc, new_doc, field_index, total_fields):
    i=0
    j=0
    doc = []
    while i<len(cur_doc) and j<len(new_doc):
        if cur_doc[i][0] == new_doc[j][0]:
            doc.append(join_docs(cur_doc[i], new_doc[j], field_index))
            i+=1
            j+=1
        elif cur_doc[i][0] < new_doc[j][0]:
            doc.append(cur_doc[i])
            i+=1
        else:
            n_doc = new_doc[j]
            tmp = []
            for field_cnt in range(total_fields):
                if field_cnt == field_index:
                    tmp.append(1)
                else:
                    tmp.append(0)
            n_doc.append(tmp)
            doc.append(n_doc)
            j+=1
    while i<len(cur_doc):
        doc.append(cur_doc[i])
        i+=1
    while j<len(new_doc):
        n_doc = new_doc[j]
        tmp = []
        for field_cnt in range(total_fields):
            if field_cnt == field_index:
                tmp.append(1)
            else:
                tmp.append(0)
        n_doc.append(tmp)
        doc.append(n_doc)
        j+=1
    return doc


# In[14]:


def sort_dict(inv_lists):
    words = sorted(inv_lists.items(), key=lambda x: len(x[1]['b']))
    return [w[0] for w in words]


# In[15]:


def get_search_results(search_terms, number_of_results):
    inv_lists = {}
    for word in search_terms:
        inv_list = get_inverted_list_of_word(word, ['t', 'b'])
        if inv_list:
            inv_lists[word] = inv_list
    words = sort_dict(inv_lists)
    cur_doc = []
    for word in words:
        if word not in inv_lists:
            continue
        if 't' in inv_lists[word]:
            cur_doc = merge_lists(cur_doc, inv_lists[word]['t'], 0, 2)
        if 'b' in inv_lists[word]:
            cur_doc = merge_lists(cur_doc, inv_lists[word]['b'], 1, 2)

    cur_doc.sort(key=lambda k: (max(k[2]), k[2], k[1], k[0]), reverse = True)
    if not cur_doc:
        return []
    results = cur_doc[:number_of_results]
    results = np.asarray(results)
    results = results[:, 0]

    return results


# In[16]:


def order_field_keys(field_keys):
    ordered = ['t', 'b', 'c', 'i', 'r', 'e']
    ret_keys = []
    for field in ordered:
        if field in field_keys:
            ret_keys.append(field)
    return ret_keys


# In[17]:


def get_field_results(field_terms, number_of_results):
    cur_doc = []
    query_words = {}
    all_fields = list(field_terms.keys())
    all_fields = order_field_keys(all_fields)
    for field in field_terms:
        for word in field_terms[field]:
            if word not in query_words:
                query_words[word] = []
            query_words[word].append(field)
    inv_lists = {}
    for word in query_words:
        inv_list = get_inverted_list_of_word(word, query_words[word])
        if inv_list:
            inv_lists[word] = inv_list
    
    cur_doc = []
    for word in query_words:
        for field in query_words[word]:
            if word in inv_lists and field in inv_lists[word]:
                cur_doc = merge_lists(cur_doc, inv_lists[word][field], all_fields.index(field), len(all_fields))
    cur_doc.sort(key=lambda k: (max(k[2]), k[2], k[1], k[0]), reverse = True)
    if not cur_doc:
        return []
    results = cur_doc[:number_of_results]
    results = np.asarray(results)
    results = results[:, 0]

    return results


# In[18]:


def print_results(query, result_count):
    search_terms, field_terms = preprocess_query(query)
    if field_terms:
        results = get_field_results(field_terms, result_count)
    else:
        results = get_search_results(search_terms, result_count)

    titles = get_titles(results)
    for title in titles:
        print(title)
#         print('http://en.wikipedia.org/wiki/' + title.replace(' ', '_'))


# In[19]:

if __name__ == '__main__':

    warnings.filterwarnings("ignore")
    number_in_one_file = 10000
    index_folder_path = sys.argv[1]
    title_folder_path = os.path.join(index_folder_path, 'titles')
    inv_idx_folder_path = os.path.join(index_folder_path, 'inv_idx')
    other_files_folder_path = os.path.join(index_folder_path, 'other_files')
    total_documents = 0
    with open(os.path.join(other_files_folder_path, 'total_count_of_documents.txt'), 'r') as f:
        for line in f.readlines():
            total_documents = int(line)
    field_mapping = {"body":'b', "category":'c', "extlink":'e', "infobox":'i', "ref":'r', "title":'t'}
    stemmer = Stemmer('porter')
    secondary_index_words = []
    with open(os.path.join(other_files_folder_path, 'words.txt'), 'r') as f:
        for line in f.readlines():
            secondary_index_words.append(line[:-1])

    while True:
        print("Enter your query")
        try:
            query = input()
        except:
            break
        a = time()
        print_results(query, 10)
        print("Time taken -> {}".format(round(time()-a, 5)))


# # TODO
# ## Do not display pages with same titles after text processing (for example do not output both shinga,peru and shinga, peru
