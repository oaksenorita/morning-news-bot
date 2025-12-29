import os
import feedparser
import requests
import google.generativeai as genai
import json

# --- 修正点1: 鍵を取り出す時に .strip() をつけて、余計な空白や改行を削除する ---
try:
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
    LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"].strip()
    LINE_USER_ID = os.environ["LINE_USER_ID"].strip()
except KeyError:
    print("エラー: Secretsが設定されていません。")
    exit(1)

RSS_URLS = [
    "https://news.yahoo.co.jp/rss/categories/business.xml",
    "https://www.watch.impress.co.jp/data/rss/1.0/fintech/feed.rdf"
]

genai.configure(api_key=GEMINI_API_KEY)

def fetch_news(urls):
    articles = []
    print("ニュース収集中...")
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                articles.append(f"- {entry.title} ({entry.link})")
        except:
            pass
    return "\n".join(articles)

def curate_news_for_line(news_text):
    # 最新モデルを指定
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    あなたは銀行の頼れる先輩社員です。
    これから入行する新人（後輩）のために、今日のニュースから「知っておくべき重要トピック」を3つ選んで教えてあげてください。

    【心がけること】
    - 難しい専門用語は使わず、噛み砕いて説明すること。
    - 「なぜ銀行員としてこれを知っておくべきか」を現場の視点で伝えること。
    - ニュースに出てくる難しそうな単語を1つピックアップして解説すること。

    【出力形式】
    -----------------------------
    【1】記事タイトル
    🗣 **先輩の解説:** 要約と、それがどう仕事に関係するかを話し言葉（〜だよ、〜なんだ）で3行くらいで。

    💡 **用語メモ:** [難しい単語]
    その単語の意味を1行で解説。

    🔗 [記事リンク]
    -----------------------------
    （これを3件繰り返す）

    ニュースリスト:
    {news_text}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI生成エラー: {e}"

def send_line_message(token, user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    # ここでエラーが起きていたので詳細を表示できるように修正
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code != 200:
            print(f"LINE送信エラー: {response.status_code} {response.text}")
    except Exception as e:
        print(f"接続エラー: {e}")

# 実行
if __name__ == "__main__":
    news_data = fetch_news(RSS_URLS)
    if news_data:
        ai_summary = curate_news_for_line(news_data)
        if ai_summary:
            send_line_message(LINE_ACCESS_TOKEN, LINE_USER_ID, ai_summary)
