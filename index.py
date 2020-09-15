#!/usr/bin/env python
# coding: utf-8

# In[2]:


import copy
import functools
import os
from pprint import pprint
import re
from spacy.lang.en.stop_words import STOP_WORDS
from Stemmer import Stemmer
import sys
from time import time
from tqdm import tqdm
import xml.sax



# In[4]:


def preprocessText(text):
    text = re.split(r'[^a-zA-Z0-9]+', text)
    for i in range(len(text)):
        text[i] = stemmer.stemWord(text[i])
    
    filtered_text = []
    for word in text:
        if word in STOP_WORDS or len(word) <= 1:
            continue
        if len(word) >= 8:
            try:
                int(word, 16)
                continue
            except:
                pass
        filtered_text.append(word)

    return filtered_text


# In[5]:


def get_category(text):
    main_text = '(.+?)(\]|\|)'
    start = '\[\[category:'
    p = re.compile(start + main_text)
    iter_found = p.finditer(text)
    cats = ""
    for match in iter_found:
        cats += match.group(1)
        cats += " "
    return preprocessText(cats)


# In[6]:


def get_external_links(text):
    query_term = "==external links=="

    # if there is no external link
    idx = text.find(query_term)
    if idx == -1:
        return []

    # reaching at start of next line
    while text[idx] != '\n':
        idx += 1
    idx += 1

    links = ""
    while idx < len(text) and text[idx]=='*':
        link = ""
        while idx < len(text) and text[idx]!='\n':
            link += text[idx]
            idx += 1
        links += link
        links += " "
        while idx < len(text) and text[idx]=='\n':
            idx += 1
    return preprocessText(links)
    


# In[7]:


def get_references(text):
    query_term = "==references=="
    
    # if there is no reference
    idx = text.find(query_term)
    if idx == -1:
        return []
    
    while text[idx] != '\n':
        idx += 1
    idx += 1
    
    refers = ""
    while idx < len(text) and ((text[idx]=='{' and text[idx+1]=='{') or text[idx]=='*'):
        refer = ""
        while idx < len(text) and text[idx]!='\n':
            refer += text[idx]
            idx += 1
        while idx < len(text) and text[idx]=='\n':
            idx += 1
            
        if 'defaultsort' in refer:
            break
        if 'reflist' in refer:
            continue
        refers+=refer
        refers+=" "

    return preprocessText(refers)


# In[8]:


def get_infobox(text):
    idx = text.find("{{infobox")
    
    if idx == -1:
        return []
    
    text = text[idx:]
    inf_bx = ""
    
    text = text.split("\n")
    break_cond = False
    
    for i in range(1, len(text)):
        line = text[i]
        if line == "}}":
            break
        for char in line:
            if char == ' ' or char == '\t':
                continue
            if char != '|':
                break_cond = True
                break
            else:
                break
        if break_cond:
            break
        line = line.split("=")
        if len(line)==1:
            break
        inf_bx += line[1]
    return preprocessText(inf_bx)


# In[9]:


def initialize_doc():
    doc = {}
    doc['b'] = []
    doc['c'] = []
    doc['e'] = []
    doc['i'] = []
    doc['r'] = []
    doc['t'] = []
    return doc


# In[10]:


def create_index(text, cur_field, inv_idx, doc_id):
    cnt_arr = {}
    for word in text:
        if word not in cnt_arr:
            cnt_arr[word] = 1
        else:
            cnt_arr[word] += 1
    for word in cnt_arr:
        if word not in inv_idx:
            inv_idx[word] = {}
        if cur_field not in inv_idx[word]:
            inv_idx[word][cur_field] = []
        inv_idx[word][cur_field].append((doc_id, cnt_arr[word]))
    return inv_idx


# In[11]:


def store_in_file(inv_idx, filename, titles):
    with open(filename, 'w') as f:
        word_list = sorted(inv_idx.keys())
        for word in word_list:
            f.write(word)
            f.write(" ")
            field_keys = sorted(inv_idx[word].keys())
            for field in field_keys:
                f.write(field)
                f.write("-")
                first = True
                for doc_id, cnt in inv_idx[word][field]:
                    if not first:
                        f.write(',')
                    first = False
                    f.write(str(doc_id))
                    f.write(":")
                    f.write(str(cnt))
                f.write(' ')
            f.write("\n")
    titles_path = os.path.join(titles_folder, 'titles.txt')
    with open(titles_path, 'a+') as f:
        first = True
        for title in titles:
            if not first:
                f.write('\n')
            first = False
            f.write(title)
            f.write(" ")
            fields = sorted(titles[title].keys())
            first = True
            for field in fields:
                if not first:
                    f.write('-')
                first = False
                f.write(str(titles[title][field]))
        f.write('\n')


# In[12]:


def index_documents(documents, titles, filename, total_docs):
    inv_idx = {}
    for doc_id in documents:
        for field_key in documents[doc_id]:
            create_index(documents[doc_id][field_key], field_key, inv_idx, doc_id)
    store_in_file(inv_idx, filename, titles)
    total_count_of_documents_path = os.path.join(other_files_folder, 'total_count_of_documents.txt')
    with open(total_count_of_documents_path, 'w') as f:
        f.write(str(total_docs))
    return


# ### Index n documents at a time and store it in disk
# #### documents attribute is a dict containing doc_id -> document dict

# In[13]:


class WikiHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.data = ""
        self.documents = {}
        self.document_limit = number_in_one_file
        self.doc_id = 0
        self.titles = {}
        self.count = 0
        self.fields = ['b', 'c', 'e', 'i', 'r', 't']

    def startElement(self, tag, attributes):
        if tag == 'page':
            self.cur_doc = initialize_doc()
        self.data = ""

    def endElement(self, tag):
        if tag == 'page':
            self.extract_field_data()
            self.documents[self.doc_id] = copy.deepcopy(self.cur_doc)
            self.doc_id += 1
            self.cur_doc.clear()
            self.data = ""

        if (tag == 'page' and self.doc_id % self.document_limit == 0) or tag == 'mediawiki':
            filename = os.path.join(inv_idx_folder, str(self.count) + ".txt")
            index_documents(self.documents, self.titles, filename, self.doc_id)
            self.documents.clear()
            self.titles.clear()
            self.count += 1

        if tag == 'text':
            self.cur_doc['b'] = self.data
            self.data = ""

        elif tag == 'title':
            self.cur_doc['t'] = self.data
            self.data = ""

    def characters(self, content):
        self.data += content
        
    def extract_field_data(self):
        title = self.cur_doc['t']
        self.cur_doc['t'] = preprocessText(title.lower())
        text = self.cur_doc['b']
        text = text.lower()
        self.cur_doc['b'] = preprocessText(text)
        self.cur_doc['c'] = get_category(text)
        self.cur_doc['e'] = get_external_links(text)
        self.cur_doc['r'] = get_references(text)
        self.cur_doc['i'] = get_infobox(text)
        for field in self.fields:
            if title not in self.titles:
                self.titles[title] = {}
            if field in self.cur_doc:
                self.titles[title][field]=len(self.cur_doc[field])
            else:
                self.titles[title][field]=0
        return


# In[15]:


def merge_two_fields(field1, field2):
    f1 = field1.split('-')
    f2 = field2.split('-')
    new_field = f1[0]
    new_field += '-'
    new_field += f1[1]
    new_field += ','
    new_field += f2[1]
    return new_field


# In[16]:


def merge_two_lines(line1, line2):
    line1 = line1.split(" ")
    line2 = line2.split(" ")
    new_line = line1[0]
    new_line += " "
    
    i = 1
    j = 1
    while i<len(line1) and j<len(line2):
        field_idx1 = line1[i]
        field_idx2 = line2[j]
        f1 = field_idx1.split('-')[0]
        f2 = field_idx2.split('-')[0]
        if f1 < f2:
            new_line += field_idx1
            new_line += " "
            i += 1
        elif f2 < f1:
            new_line += field_idx2
            new_line += " "
            j += 1
        else:
            new_line += merge_two_fields(field_idx1, field_idx2)
            new_line += " "
            i += 1
            j += 1
    while i<len(line1):
        field_idx1 = line1[i]
        new_line += field_idx1
        new_line += " "
        i += 1
    while j<len(line2):
        field_idx2 = line2[j]
        new_line += field_idx2
        new_line += " "
        j += 1
    return new_line
    


# In[17]:


def merge_two_files(file1, file2):
    file1 = os.path.join(inv_idx_folder, file1)
    file2 = os.path.join(inv_idx_folder, file2)
    new_file = os.path.join(inv_idx_folder, "tmp.txt")
    with open(file1, 'r') as f1:
        with open(file2, 'r') as f2:
            with open(new_file, 'w+') as f3:
                line1 = f1.readline().strip()
                line2 = f2.readline().strip()

                while line1 and line2:
                    word1 = line1.split(" ")[0]
                    word2 = line2.split(" ")[0]

                    if word1 < word2:
                        f3.write(line1)
                        f3.write('\n')
                        line1 = f1.readline().strip()
                    elif word2 < word1:
                        f3.write(line2)
                        f3.write('\n')
                        line2 = f2.readline().strip()
                    else:
                        f3.write(merge_two_lines(line1, line2))
                        f3.write('\n')
                        line1 = f1.readline().strip()
                        line2 = f2.readline().strip()
                while line1:
                    f3.write(line1)
                    f3.write('\n')
                    line1 = f1.readline().strip()
                while line2:
                    f3.write(line2)
                    f3.write('\n')
                    line2 = f2.readline().strip()
    os.remove(file1)
    os.remove(file2)
    os.rename(new_file, file1)
    return


# In[18]:


def compare(item1, item2):
    item1 = int(item1.split('.')[0])
    item2 = int(item2.split('.')[0])
    if item1 < item2:
        return -1
    else:
        return 1


# In[19]:


def merge():
    files = os.listdir(inv_idx_folder)
    files = sorted(files, key=functools.cmp_to_key(compare))
    while len(files) != 1:
        i = 0
        while i < len(files)-1:
            merge_two_files(files[i], files[i+1])
            i += 2
        files = os.listdir(inv_idx_folder)
        files = sorted(files, key=functools.cmp_to_key(compare))


# In[20]:


def divide_file(filename, secondary_index_filename = None):
    file_counter = 1
    doc_counter = 0
    with open(filename, 'r') as f1:
        line = f1.readline()
        while line:
            if not secondary_index_filename:
                new_filename = os.path.join(titles_folder, str(file_counter) + '.txt')
            else:
                new_filename = os.path.join(inv_idx_folder, str(file_counter) + '.txt')
            with open(new_filename, 'w') as f2:
                doc_counter = 1
                first = True
                while line and doc_counter != number_in_one_file+1:
                    if secondary_index_filename and first:
                        with open(secondary_index_filename, 'a+') as w:
                            w.write(line.split(' ')[0])
                            w.write('\n')
                    first = False
                    f2.write(line)
                    line = f1.readline()
                    doc_counter += 1
                file_counter += 1
    os.remove(filename)


# In[21]:

if __name__ == '__main__':
	start_time = time()
	number_in_one_file = 10000
	stemmer = Stemmer('porter')
	dump_path = sys.argv[1]
	index_folder_path = sys.argv[2]

	if not os.path.exists(index_folder_path):
	    os.makedirs(index_folder_path)

	inv_idx_folder = os.path.join(index_folder_path, 'inv_idx')
	if not os.path.exists(inv_idx_folder):
	    os.makedirs(inv_idx_folder)
	    
	titles_folder = os.path.join(index_folder_path, 'titles')
	if not os.path.exists(titles_folder):
	    os.makedirs(titles_folder)

	other_files_folder = os.path.join(index_folder_path, 'other_files')
	if not os.path.exists(other_files_folder):
	    os.makedirs(other_files_folder)

	parser = xml.sax.make_parser()
	parser.setFeature(xml.sax.handler.feature_namespaces, 0)

	Handler = WikiHandler()
	parser.setContentHandler(Handler)
	parser.parse(dump_path)


	merge()
	main_inv_idx_file_path = os.path.join(inv_idx_folder, '0.txt')
	secondary_idx_file_path = os.path.join(other_files_folder, 'words.txt')
	divide_file(main_inv_idx_file_path, secondary_idx_file_path)

	titles_file_path = os.path.join(titles_folder, 'titles.txt')
	divide_file(titles_file_path)
	print("Total time taken in indexing is {}".format(time() - start_time))

