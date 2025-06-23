from flask import Flask, request, jsonify
from utils import *

app = Flask(__name__)
current_lang = 'en'

@app.route("/")
def home():
    return "✅ Onimo AI Lite is Live on Render!"

@app.route('/ask', methods=['POST'])
def ask():
    global current_lang
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Please provide a valid question."})

    lang = detect_language(query)
    query_en = translate_text(query, target_lang='en').lower()

    if any(x in query_en for x in ["bangla te kotha bolo", "বাংলায় কথা বলো", "talk bangla"]):
        current_lang = 'bn'
        msg = translate_text("From now, I will speak Bangla.", target_lang=current_lang)
        return jsonify({"status": "language_changed", "message": msg})

    if any(x in query_en for x in ["talk english", "speak english"]):
        current_lang = 'en'
        msg = translate_text("From now, I will speak English.", target_lang=current_lang)
        return jsonify({"status": "language_changed", "message": msg})

    if any(x in query_en for x in ["hi", "hello", "hey"]):
        msg = translate_text("Hello! How can I help you?", target_lang=current_lang)
        return jsonify({"status": "chat", "message": msg})

    if "creator" in query_en or "who created you" in query_en or "তোমার নির্মাতা" in query:
        msg = translate_text(f"My creator is {CREATOR_NAME}.", target_lang=current_lang)
        return jsonify({"status": "info", "message": msg})

    detailed = is_detailed_query(query)
    keyword = extract_keywords(query_en)

    summary, source = fetch_wikipedia_summary(keyword, 'en', detailed)
    if summary:
        return jsonify({
            "status": "wiki",
            "summary": translate_text(summary, target_lang=current_lang),
            "source": source,
            "language": current_lang
        })

    news, link = fetch_latest_news(keyword, detailed)
    if news:
        return jsonify({
            "status": "news",
            "summary": translate_text(news, target_lang=current_lang),
            "source": link,
            "language": current_lang
        })

    msg = translate_text("Sorry, I couldn't find enough information.", target_lang=current_lang)
    return jsonify({"status": "unknown", "message": msg})


@app.route('/youtube', methods=['POST'])
def youtube_fact_check():
    global current_lang
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "message": "Please provide a valid YouTube link."})

    video_id = extract_youtube_id(url)
    if not video_id:
        return jsonify({"status": "error", "message": "Invalid YouTube URL."})

    full_text = get_transcript_flexible(video_id)
    if not full_text:
        return jsonify({"status": "error", "message": "Transcript not found."})

    keyword = extract_keywords(full_text)

    summary, source = fetch_wikipedia_summary(keyword, 'en', False)
    if summary:
        return jsonify({
            "status": "youtube_wiki",
            "summary": translate_text(summary, target_lang=current_lang),
            "source": source,
            "language": current_lang
        })

    news, link = fetch_latest_news(keyword, False)
    if news:
        return jsonify({
            "status": "youtube_news",
            "summary": translate_text(news, target_lang=current_lang),
            "source": link,
            "language": current_lang
        })

    return jsonify({
        "status": "unknown",
        "message": translate_text("Couldn't fact check the video content.", target_lang=current_lang)
    })


@app.route('/health')
def health():
    return "Onimo AI Lite ✅ Running"


if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port)
