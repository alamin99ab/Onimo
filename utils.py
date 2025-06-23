from flask import request, jsonify
from langdetect import detect
from deep_translator import GoogleTranslator
from urllib.parse import quote
import wikipedia
import requests
import re
from youtube_transcript_api import YouTubeTranscriptApi
from keybert import KeyBERT
from concurrent.futures import ThreadPoolExecutor, as_completed
import spacy

CREATOR_NAME = "Alamin"
NEWS_API_KEY = "65e2964fd2d548eba7f26eaf17cbed75"
supported_langs = ['en', 'bn']
current_lang = 'en'
kw_model = KeyBERT(model='all-MiniLM-L6-v2')
nlp = spacy.load("en_core_web_sm")


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
    cues = [
        "বিস্তারিত", "details", "full information", "সম্পূর্ণ তথ্য",
        "bistarito", "bistarito bolo", "bistarito bol", "details please"
    ]
    query_lower = query.lower()
    return any(word in query_lower for word in cues)


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
    url = f"https://newsapi.org/v2/everything?q={quote(query)}&language=en&pageSize={3 if detailed else 1}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "ok" and data.get("articles"):
            article = data["articles"][0]
            title = article["title"]
            desc = article.get("description", "")
            url = article["url"]
            return f"{title}: {desc}", url
    except:
        pass
    return None, None


def extract_youtube_id(url):
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid YouTube URL.")


def get_transcript_flexible(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[
            'en', 'en-US', 'bn', 'hi', 'ar', 'zh-Hant', 'nl', 'fr', 'de', 'id', 'it', 'ja', 'ko', 'pt', 'ru',
            'es', 'th', 'tr', 'uk', 'vi'
        ])
        return " ".join([t['text'] for t in transcript])
    except Exception as e:
        return None


def extract_keywords(text):
    try:
        keywords = kw_model.extract_keywords(text, stop_words='english', top_n=1)
        if keywords:
            return keywords[0][0]
        doc = nlp(text)
        entities = [ent.text for ent in doc.ents if ent.label_ in ["PERSON", "ORG", "GPE", "EVENT", "WORK_OF_ART"]]
        if entities:
            return entities[0]
    except:
        pass
    return " ".join(text.split()[:3])


# ✅ ask route with `global current_lang`
def ask():
    global current_lang

    data = request.get_json()
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"status": "error", "message": "Please provide a valid question."})

    lang = detect_language(query)
    query_en = translate_text(query, target_lang='en')
    query_lower = query_en.lower()

    if any(kw in query_lower for kw in ["bangla te kotha bolo", "বাংলায় কথা বলো", "talk bangla", "speak bangla"]):
        current_lang = 'bn'
        msg = translate_text("From now, I will speak Bangla.", target_lang=current_lang)
        return jsonify({"status": "language_changed", "message": msg})

    if any(kw in query_lower for kw in ["english e kotha bolo", "talk english", "speak english"]):
        current_lang = 'en'
        msg = translate_text("From now, I will speak English.", target_lang=current_lang)
        return jsonify({"status": "language_changed", "message": msg})

    if any(word in query_lower for word in ["hi", "hello", "hey", "hallo"]):
        msg = translate_text("Hello! How can I help you?", target_lang=current_lang)
        return jsonify({"status": "chat", "message": msg})

    if "creator" in query_lower or "who created you" in query_lower or "তোমার নির্মাতা" in query:
        msg = translate_text(f"My creator is {CREATOR_NAME}.", target_lang=current_lang)
        return jsonify({"status": "info", "message": msg})

    detailed = is_detailed_query(query)
    keyword = extract_keywords(query_en)

    with ThreadPoolExecutor() as executor:
        tasks = {
            executor.submit(fetch_wikipedia_summary, keyword, 'en', detailed): "wiki",
            executor.submit(fetch_latest_news, keyword, detailed): "news"
        }
        for future in as_completed(tasks):
            source = tasks[future]
            try:
                result = future.result()
                if result and result[0]:
                    translated_summary = translate_text(result[0], target_lang=current_lang)
                    return jsonify({
                        "status": f"{source}_detailed" if detailed else source,
                        "summary": translated_summary,
                        "source": result[1],
                        "language": current_lang
                    })
            except:
                pass

    msg = translate_text("Sorry, I couldn't find enough information.", target_lang=current_lang)
    return jsonify({"status": "unknown", "message": msg})


# ✅ youtube_fact_check route with `global current_lang`
def youtube_fact_check():
    global current_lang

    data = request.get_json()
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"status": "error", "message": "Please provide a valid YouTube link."})

    try:
        video_id = extract_youtube_id(url)
        full_text = get_transcript_flexible(video_id)

        if not full_text:
            return jsonify({"status": "error", "message": "Could not retrieve transcript. Check language availability."})

        keyword = extract_keywords(full_text)

        with ThreadPoolExecutor() as executor:
            tasks = {
                executor.submit(fetch_wikipedia_summary, keyword, 'en', False): "wiki",
                executor.submit(fetch_latest_news, keyword, False): "news"
            }
            for future in as_completed(tasks):
                source = tasks[future]
                try:
                    result = future.result()
                    if result and result[0]:
                        translated_summary = translate_text(result[0], target_lang=current_lang)
                        return jsonify({
                            "status": f"youtube_{source}",
                            "summary": translated_summary,
                            "source": result[1],
                            "language": current_lang
                        })
                except:
                    pass

        return jsonify({"status": "unknown", "message": translate_text("Couldn't fact check the video content.", target_lang=current_lang)})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# Route registration helper for app.py
def register_routes(app):
    app.add_url_rule('/ask', view_func=ask, methods=['POST'])
    app.add_url_rule('/youtube', view_func=youtube_fact_check, methods=['POST'])
