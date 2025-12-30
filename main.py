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

# ニュースソース（北海道の地域ニュースを追加）
RSS_URLS = [
    "https://news.yahoo.co.jp/rss/categories/business.xml",      # 経済
    "https://www.watch.impress.co.jp/data/rss/1.0/fintech/feed.rdf", # Fintech
    "https://news.yahoo.co.jp/rss/regions/hokkaido.xml"          # 北海道のニュース
]

genai.configure(api_key=GEMINI_API_KEY)

# 1. ニュースを取得
def fetch_news(urls):
    articles = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: # 各5件ほど取得
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
        
        # 必要な情報だけ抽出
        weather_desc = data["weather"][0]["description"] # 天気（雨、曇りなど）
        temp = data["main"]["temp"]       # 現在気温
        temp_max = data["main"]["temp_max"] # 最高気温
        temp_min = data["main"]["temp_min"] # 最低気温
        
        return f"天気: {weather_desc}, 気温: {temp}℃ (最高:{temp_max}℃ / 最低:{temp_min}℃)"
    except Exception as e:
        return f"天気取得エラー: {e}"

# 3. AIによる編集・執筆
def create_morning_briefing(news_text, weather_text):
    # 指定のモデルを使用
    model = genai.GenerativeModel('gemini-flash-latest')
    
    # 今日の日付
    today = datetime.date.today().strftime("%Y/%m/%d")

    prompt = f"""
    今日は {today} です。
    あなたは「北海道の地方銀行」に内定した新人に対し、毎朝の情報を届けるアシスタントです。
    以下の「ニュースリスト」と「札幌の天気」を元に、LINE通知用のメッセージを作成してください。

    【トーンの指定】
    - 堅苦しすぎず、かつ砕けすぎない「丁寧でわかりやすい敬語（です・ます調）」で書いてください。
    - 絵文字は適度に使用してください（使いすぎない）。

    【構成】
    1. **挨拶**: 今日の日付と、札幌の天気に触れた短い挨拶。
    2. **服装予報**: 
       - 今日の札幌の天気と気温に基づき、一般的な男性としての適切な服装を具体的に提案してください（例：路面凍結への注意や、アウターの厚さなど）。
    3. **今日の注目ニュース（3本）**:
       - 以下のリストから、地銀職員として知っておくべき記事を3つ選んでください。
       - 選定基準: 金融・経済、北海道の地域経済、Fintech、規制緩和など。
       - 各記事について、「要約」と「地銀内定者としての視点（なぜ重要か）」を簡潔に解説してください。

    【ニュースリスト】
    {news_text}

    【札幌の天気データ】
    {weather_text}
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
    # 情報を集める
    news_data = fetch_news(RSS_URLS)
    weather_data = fetch_weather_sapporo()
    
    # AIが原稿を書く
    if news_data:
        message = create_morning_briefing(news_data, weather_data)
        # LINEに送る
        send_line_message(LINE_ACCESS_TOKEN, LINE_USER_ID, message)
