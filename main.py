import os
import feedparser
import requests
import google.generativeai as genai
import json
import datetime

# --- 設定・鍵の取得 ---
try:
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
    LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"].strip()
    LINE_USER_ID = os.environ["LINE_USER_ID"].strip()
    OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"].strip()
except KeyError:
    print("エラー: Secretsの設定が足りません。")
    exit(1)

# ニュースソース（北海道と金融中心）
RSS_URLS = [
    "https://news.yahoo.co.jp/rss/categories/business.xml",      # 経済
    "https://www.watch.impress.co.jp/data/rss/1.0/fintech/feed.rdf", # Fintech
    "https://news.yahoo.co.jp/rss/regions/hokkaido.xml"          # 北海道
]

genai.configure(api_key=GEMINI_API_KEY)

# 1. ニュースを取得
def fetch_news(urls):
    articles = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                # AIがリンクを認識しやすいようにマークダウン形式にしておく
                articles.append(f"- {entry.title} ({entry.link})")
        except:
            pass
    return "\n".join(articles)

# 2. 天気を取得（札幌）
def fetch_weather_sapporo():
    city = "Sapporo,jp"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        weather_desc = data["weather"][0]["description"]
        temp_max = data["main"]["temp_max"]
        temp_min = data["main"]["temp_min"]
        
        # 服装などの余計な情報は含めず、データのみを返す
        return f"天気: {weather_desc}, 最高気温: {temp_max}℃, 最低気温: {temp_min}℃"
    except Exception as e:
        return f"天気取得エラー: {e}"

# 3. AIによる編集・執筆（ここを大幅強化）
def create_morning_briefing(news_text, weather_text):
    model = genai.GenerativeModel('gemini-flash-latest')
    today = datetime.date.today().strftime("%Y/%m/%d")

    prompt = f"""
    今日は {today} です。
    あなたは北海道の地方銀行に内定した新人に対し、プロフェッショナルな情報を提供するアシスタントです。

    【出力構成】
    
    ## 🌤 {today} 札幌の天気
    {weather_text}
    （※余計な挨拶や服装のアドバイスは不要です。上記のデータのみ記載してください）

    ## 📰 今日の重要ニュース（3選）
    以下のニュースリストから、地銀内定者が読むべき重要な記事を3つ選定し、以下のフォーマットで解説してください。

    ### [記事タイトル]
    
    **1. ロジカル要約**
    * **背景/経緯:** (この記事に至るまでの前提や課題)
    * **事象:** (具体的に何が起きたか、何が決まったか)
    * **結果/影響:** (それにより今後どうなると予想されるか)
    
    **2. 地銀視点の深掘り**
    * 単に「重要だ」と言うだけでなく、「取引先企業（中小企業など）にどう影響するか」「もし顧客と話すならどういう話題になるか」まで踏み込んで記述してください。
    
    🔗 [記事のURL]

    (これを3記事分繰り返す)

    【対象ニュースリスト】
    {news_text}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI生成エラー: {e}"

# 4. LINE送信
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
    requests.post(url, headers=headers, data=json.dumps(data))

# メイン処理
if __name__ == "__main__":
    news_data = fetch_news(RSS_URLS)
    weather_data = fetch_weather_sapporo()
    
    if news_data:
        message = create_morning_briefing(news_data, weather_data)
        send_line_message(LINE_ACCESS_TOKEN, LINE_USER_ID, message)
