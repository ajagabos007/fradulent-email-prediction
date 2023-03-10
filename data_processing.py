from scipy.sparse import csr_matrix
import pandas as pd
import numpy as np
import os
import email
import email.policy
import nltk 
from collections import Counter
from bs4 import BeautifulSoup
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
import pickle


def get_email_structure(email):
    if isinstance(email, str): #if email is a string, it is basically already in plain text so just return the email type
        return email 
    payload = email.get_payload()
    if isinstance (payload, list): #if email payload is a list then it means there are multiple emails, so we loop through all the emails in the list and return each email type the "get email structure" function
        return 'multipart({})'.format(', '.join([get_email_structure(sub_email) for sub_email in payload])) #kinda recursive lol
    else: 
        return email.get_content_type()

def structures_counter(emails):
    structures = Counter()
    for email in emails:
        structure = get_email_structure(email)
        structures[structure] += 1 #basically just increasing the value count (frequency) by 1
    return structures 


def html_to_plain(email):
    try:
        soup = BeautifulSoup(email.get_content(), 'html.parser')
        return soup.text.replace('\n\n', '')
    except:
        return 'empty'
    
def email_to_plain(email):
    struct = get_email_structure(email)
    for part in email.walk():
        part_content_type = part.get_content_type()
        if part_content_type not in ['text/plain', 'test/html']:
            continue 
        try:
            part_content = part.get_content()
        except:  #in case of encoding issues
            part_content = str(part.get_payload())
        if part_content_type == 'text/plain':
            return part_content 
        else:
            return html_to_plain(part)

class EmailToWords(BaseEstimator, TransformerMixin):
    def __init__(self, stripHeaders=True, lowercaseConversion=True, punctuationRemoval=True, urlReplace=True, numberReplacement=True, stemming=True):
        self.stripHeaders = stripHeaders
        self.punctuationRemoval = punctuationRemoval
        self.urlReplace = urlReplace
        self.numberReplacement = numberReplacement
        self.stemming = stemming
        self.stemmer = nltk.PorterStemmer()
        self.lowercaseConversion = lowercaseConversion
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):
        X_to_words = []
        for email in X:
            text = email_to_plain(email)
            if text is None:
                text = 'empty'
            if self.lowercaseConversion:
                text = text.lower()
            
            if self.punctuationRemoval:
                text = text.replace('.', '')
                text = text.replace(',', '')
                text = text.replace('!', '')
                text = text.replace('?', '')
            
            word_count = Counter(text.split())
            if self.stemming:
                stemmed_word_count = Counter()
                for word, count in word_count.items():
                    stemmed_word = self.stemmer.stem(word)
                    stemmed_word_count[stemmed_word] += count
                word_counts = stemmed_word_count
            X_to_words.append(word_count)
        return np.array(X_to_words)

class WordCountToVector(BaseEstimator, TransformerMixin):
    def __init__(self, vocabulary_size=1000):
        self.vocabulary_size = vocabulary_size
    
    def fit(self, X, y=None):
        total_word_count = Counter()
        for word_count in X:
            for word, count in word_count.items():
                total_word_count[word] += min(count, 10)
        self.most_common = total_word_count.most_common()[:self.vocabulary_size]
        self.vocabulary_ = {word: index + 1 for index, (word, count) in enumerate(self.most_common)}
        return self
    
    def transform(self, X, y=None):
        rows = []
        cols = []
        data = []

        for row, word_count in enumerate(X):
            for word, count in word_count.items():
                rows.append(row)
                cols.append(self.vocabulary_.get(word, 0))
                data.append(count)
            # print(len(data))
            # print(len(rows))
            # print(len(cols))
        return csr_matrix((data, (rows, cols)), shape=(len(X), self.vocabulary_size + 1))


email_pipeline = Pipeline([
    ('Email To Words', EmailToWords()),
    ('Word Count To Vectors', WordCountToVector()),
])

#load file
def load_email(filename):
    with open(filename, 'rb') as f:
        return email.parser.BytesParser(policy=email.policy.default).parse(f)

def predict_spam(data):
    augmented_data = email_pipeline.fit_transform([data])
    model = pickle.load(open('finalized_model.sav', 'rb'))
    result = model.predict(augmented_data)
    return result

# j = "spam/0001.bfc8d64d12b325ff385cca8d07b84288"
data = load_email("email_messages/3.eml")
result = predict_spam(data)
print(result)
