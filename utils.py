from flask import request, jsonify
from langdetect import detect
from deep_translator import GoogleTranslator
from urllib.parse import quote
import wikipedia
import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi

CREATOR_NAME = "Alamin"
NEWS_API_KEY = "65e2964fd2d548eba7f26eaf17cbed75"
supported_langs = ['en', 'bn']

def detect_language(text):
    try:
        lang = detect(text)
        return lang if lang in supported_langs else 'en'
    except:
        return 'en'

def translate_text(text, target_lang='en'):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except:
        return text

def is_detailed_query(query):
    cues = ["বিস্তারিত", "details", "full information", "সম্পূর্ণ তথ্য", "bistarito"]
    return any(cue in query.lower() for cue in cues)

def extract_keywords(text):
    try:
        words = text.strip().split()
        return " ".join(words[:3]) if len(words) >= 3 else text
    except:
        return text

def fetch_wikipedia_summary(query, lang='en', detailed=False):
    try:
        wikipedia.set_lang(lang)
        results = wikipedia.search(query)
        if not results:
            return None, None
        title = results[0]
        summary = wikipedia.summary(title, sentences=5 if detailed else 2)
        url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
        return summary, url
    except:
        return None, None

def fetch_latest_news(query, detailed=False):
    try:
        url = f"https://newsapi.org/v2/everything?q={quote(query)}&language=en&pageSize={3 if detailed else 1}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
        res = requests.get(url)
        data = res.json()
        if data.get("status") == "ok" and data.get("articles"):
            article = data["articles"][0]
            title = article.get("title", "")
            desc = article.get("description", "")
            return f"{title}: {desc}", article.get("url", "")
    except:
        pass
    return None, None

def extract_youtube_id(url):
    try:
        match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
        return match.group(1) if match else None
    except:
        return None

def get_transcript_flexible(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t['text'] for t in transcript])
    except:
        return None
