import pandas as pd
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from nltk.corpus import wordnet
import re

nltk.download('punkt')
nltk.download('wordnet')

# Latent Semantic Analysis (LSA) function
def LSA(text):
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(text)
    
    lsa = TruncatedSVD(n_components=1, n_iter=100)
    lsa.fit(X)
    
    terms = vectorizer.get_feature_names_out()
    concept_words = {}

    for j, comp in enumerate(lsa.components_):
        component_terms = zip(terms, comp)
        sorted_terms = sorted(component_terms, key=lambda x: x[1], reverse=True)[:10]
        concept_words[str(j)] = sorted_terms
     
    sentence_scores = []
    for key in concept_words.keys():
        for sentence in text:
            words = nltk.word_tokenize(sentence)
            scores = 0
            for word in words:
                for word_with_scores in concept_words[key]:
                    if word == word_with_scores[0]:
                        scores += word_with_scores[1]
            sentence_scores.append(scores)
    return sentence_scores

# Text cleaning function
def clean_text(text):
    text = re.sub(r"\W", " ", text)
    text = re.sub(r"\d", " ", text)
    text = re.sub(r"\s+[a-z]\s+", " ", text)
    text = re.sub(r"^[a-z]\s+", " ", text)
    text = re.sub(r"\s+[a-z]$", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Analyze reviews to detect fake ones
def analyze_reviews(dataset):
    product_df = dataset.groupby("product_id")
    unique_products = dataset["product_id"].unique()
    no_products = len(unique_products)

    remove_reviews = []

    for i in range(no_products):
        df = product_df.get_group(unique_products[i])
        unique_reviews = df.index.tolist()
        no_reviews = len(unique_reviews)

        count = no_reviews
        reviews = []
        review_id = []

        for j in range(no_reviews):
            text = str(df.loc[unique_reviews[j]]["review_body"])
            text = clean_text(text)
            words = nltk.word_tokenize(text)

            if len(words) <= 1 and (len(text) <= 1 or not wordnet.synsets(text)):
                remove_reviews.append(unique_reviews[j])
                count -= 1
                continue

            review_id.append(unique_reviews[j])
            reviews.append(text)

        if count <= 0:
            continue

        if count == 1:
            text = [text, str(df.loc[review_id[0]]["product_title"])]
            sentence_scores = LSA(text)
            if sentence_scores[0] == 0:
                remove_reviews.append(review_id[0])
            continue

        sentence_scores = LSA(reviews)
        for j in range(len(sentence_scores)):
            if sentence_scores[j] == 0.00:
                remove_reviews.append(review_id[j])

    return remove_reviews
