import pickle
import pandas as pd
import re
import nltk
from rank_bm25 import BM25Okapi
from nltk.corpus import stopwords
import ipywidgets as widgets
import requests
from requests.exceptions import HTTPError, ConnectionError
import numpy as np # linear algebra

SEARCH_DISPLAY_COLUMNS = ['title', 'abstract', 'doi', 'authors', 'journal']
english_stopwords = list(set(stopwords.words('english')))

class WordTokenIndex:
    
    def __init__(self, 
                 corpus: pd.DataFrame, 
                 columns=SEARCH_DISPLAY_COLUMNS):
        self.corpus = corpus
        raw_search_str = self.corpus.abstract.fillna('') + ' ' + self.corpus.title.fillna('')
        self.index = raw_search_str.apply(preprocess).to_frame()
        self.index.columns = ['terms']
        self.index.index = self.corpus.index
        self.columns = columns
    
    def search(self, search_string):
        search_terms = preprocess(search_string)
        result_index = self.index.terms.apply(lambda terms: any(i in terms for i in search_terms))
        results = self.corpus[result_index].copy().reset_index().rename(columns={'index':'paper'})
        return SearchResults(results, self.columns + ['paper'])

class RankBM25Index(WordTokenIndex):
    
    def __init__(self, corpus: pd.DataFrame, columns=SEARCH_DISPLAY_COLUMNS):
        super().__init__(corpus, columns)
        self.bm25 = BM25Okapi(self.index.terms.tolist())
        
    def search(self, search_string, n=10):
        search_terms = preprocess(search_string)
        doc_scores = self.bm25.get_scores(search_terms)
        ind = np.argsort(doc_scores)[::-1][:n]
        results = self.corpus.iloc[ind][self.columns]
        results['Score'] = doc_scores[ind]
        results = results[results.Score > 0]
        return SearchResults(results.reset_index(), self.columns + ['Score'])

class Paper:
    
    '''
    A single research paper
    '''
    def __init__(self, item):
        self.paper = item.to_frame().fillna('')
        self.paper.columns = ['Value']
    
    def doi(self):
        return self.paper.loc['doi'].values[0]
    
    def text(self):
        '''
        Load the paper from doi.org and display as text. Requires Internet to be ON
        '''
        text = get(self.doi())
        return text
    
    def abstract(self):
        return self.paper.loc['abstract'].values[0]

    def html(self):
        '''
        Load the paper from doi.org and display as HTML. Requires internet to be ON
        '''
        text = get(self.doi())
        return widgets.HTML(text)
    
    def title(self):
        return self.paper.loc['title'].values[0]
    
    def authors(self, split=False):
        '''
        Get a list of authors
        '''
        authors = self.paper.loc['authors'].values[0]
        if not authors:
            return []
        if not split:
            return authors
        if authors.startswith('['):
            authors = authors.lstrip('[').rstrip(']')
            return [a.strip().replace("\'", "") for a in authors.split("\',")]
        
        # Todo: Handle cases where author names are separated by ","
        return [a.strip() for a in authors.split(';')]
        
    def _repr_html_(self):
        return self.paper._repr_html_()

def get(url, timeout=6):
    try:
        r = requests.get(url, timeout=timeout)
        return r.text
    except ConnectionError:
        print(f'Cannot connect to {url}')
        print(f'Remember to turn Internet ON in the Kaggle notebook settings')
    except HTTPError:
        print('Got http error', r.status, r.text)

def strip_characters(text):
    t = re.sub('\(|\)|:|,|;|\.|’|”|“|\?|%|>|<', '', text)
    t = re.sub('/', ' ', t)
    t = t.replace("'",'')
    return t

def clean(text):
    t = text.lower()
    t = strip_characters(t)
    return t

def tokenize(text):
    words = nltk.word_tokenize(text)
    return list(set([word for word in words 
                     if len(word) > 1
                     and not word in english_stopwords
                     and not (word.isnumeric() and len(word) is not 4)
                     and (not word.isnumeric() or word.isalpha())] )
               )

def preprocess(text):
    t = clean(text)
    tokens = tokenize(t)
    return tokens

class SearchResults:
    
    def __init__(self, 
                 data: pd.DataFrame,
                 columns = None):
        self.results = data
        if columns:
            self.results = self.results[columns]
            
    def __getitem__(self, item):
        return Paper(self.results.loc[item])
    
    def __len__(self):
        return len(self.results)
        
    def _repr_html_(self):
        return self.results._repr_html_()

'''
Init
'''

with open('mypickle.pickle', 'rb') as f:
    bm25_index = pickle.load(f)

SearchTerms = input('Terms: ')

search_results = bm25_index.search(SearchTerms, n=100)

print(search_results[0].doi())