from transformers import pipeline

nlp = pipeline("sentiment-analysis", model="bardsai/twitter-sentiment-pl-base")
print(nlp("Która godzina?"))
