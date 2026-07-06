# pip install transformers spacy torch torchvision
# python -m spacy download en_core_web_sm

import pandas as pd
import spacy
from transformers import pipeline

nlp = spacy.load("en_core_web_sm")
def remove_geography(text):
    if not isinstance(text, str):
        return ""
    doc = nlp(text)
    # remove geopolitical entities and locations
    # why? mggg models were overfitting to geography
    clean_text = " ".join([token.text for token in doc if token.ent_type_ not in ['GPE', 'LOC']])
    return clean_text

# load data
df = pd.read_csv("mo/data/MOCumulativeAug10.csv")
df['clean_text'] = df['text'].apply(remove_geography)


# load classifier
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# agggregating communities paper labels
candidate_labels = [
    "Agriculture", "Cities", "Community engagement", "Cost of living", 
    "Culture", "Diversity", "Economy and Commerce", "Environment", 
    "Ideology", "Infrastructure", "Elderly", "Family and Children", 
    "K-12 Education", "Named neighborhood", "NIMBY", "Policing", 
    "Poverty", "Recreation and Tourism", "Religion", "Suburbs", 
    "Technology", "University", "Violence", "Vulnerable populations"
]

def categorize_comment(text):
    if len(text.strip()) < 5:
        return "Unknown"
    result = classifier(text, candidate_labels, multi_label=False)
    
    # top probability label
    return result['labels'][0]




#df.to_csv('MOCategorizedComments.csv')
#df['predicted_category'] = df['clean_text'].apply(categorize_comment)
'''
test = df.head(10)
test['predicted_category'] = test['clean_text'].apply(categorize_comment)


for index, row in test.iterrows():
    print(f"\noriginal text: {row['text']}...")
    print(f"predicted category: {row['predicted_category']}")
'''

