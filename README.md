# AI-Powered Phishing Email Detection Using Natural Language Processing

## 📋 Project Overview
This project implements an AI-powered system to detect phishing emails using Natural Language Processing (NLP) techniques. It compares multiple machine learning models to identify phishing attempts based on email content analysis.

## 🎯 Objectives
- Collect and preprocess phishing and legitimate email datasets
- Apply NLP techniques (tokenization, lemmatization, TF-IDF)
- Implement and compare multiple ML models
- Evaluate performance using accuracy, precision, recall, and F1-score
- Provide a functional prediction interface

## 🛠️ Technologies Used
- **Python 3.8+**
- **Libraries**: pandas, numpy, scikit-learn, nltk, spacy, matplotlib, seaborn
- **Machine Learning Models**: Naïve Bayes, Logistic Regression, SVM, Random Forest
- **NLP Techniques**: TF-IDF, tokenization, lemmatization, stop-word removal

## 📁 Project Structure

phishing-detection-nlp/
│
├── data/ # Dataset storage
├── src/ # Source code modules
├── models/ # Saved trained models
├── results/ # Evaluation results and visualizations
├── notebooks/ # Jupyter notebooks for analysis
├── main.py # Main application entry point
└── requirements.txt # Dependencies