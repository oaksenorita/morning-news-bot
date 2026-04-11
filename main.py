import os
import feedparser
import requests
import google.generativeai as genai
import json
import datetime

try:
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()
    LINE_ACCESS_TOKEN = os.environ["LINE_ACCESS_TOKEN"].strip()
    LINE_USER_ID = os.environ["LINE_USER_ID"].strip()
    OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"].strip()
except KeyError:
    print("エラー: Secretsの設定が足りません。")
    exit(1)

RSS_URLS = [
    "https://news.yahoo.co.jp/rss/categories/business.xml",
    "https://www.watch.impress.co.jp/data/rss/1.0/fintech/feed.rdf",
    "https://news.yahoo.co.jp/rss/regions/hokkaido.xml"
]

genai.configure(api_key=GEMINI_API_KEY)

def fetch_news(urls):
    articles = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                articles.append(f"- {entry.title} ({entry.link})")
        except:
            pass
    return "\n".join(articles)

def fetch_weather_sapporo():
    city = "Sapporo,jp"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    try:
        response = requests.get(url)
        data = response.json()
        return f"天気: {data['weather'][0]['description']}, 最高気温: {data['main']['temp_max']}℃, 最低気温: {data['main']['temp_min']}℃"
    except:
        return "天気データ取得エラー"

def create_html_news(news_text, weather_text):
    model = genai.GenerativeModel('gemini-flash-latest')
    today = datetime.date.today().strftime("%Y年%m月%d日")

    prompt = f"""
    今日は {today} です。あなたは北海道の地方銀行に内定した新人向けのアシスタントです。
    以下のニュースと天気から、洗練された「1枚のHTMLページ」を作成してください。

    【HTMLの要件】
    - <!DOCTYPE html> から始める完全なHTML5で出力すること（```html などのMarkdownブロックは不要）。
    - <head>内に以下のCSSを必ず読み込むこと: <link rel="stylesheet" href="[https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css](https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css)">
    - <body>タグの中に、<main class="container"> を配置してレイアウトすること。
    
    【構成内容】
    1. ヘッダー: <h1>☀️ 朝のインサイト ({today})</h1>
    2. 天気: <article>タグの中に {weather_text} を見やすく配置。
    3. ニュース解説 (3件厳選): 以下のニュースから3つ選び、それぞれを <article> タグで囲む。
       - <h3>タグで記事タイトル
       - <b>ロジカル要約</b>: 背景/経緯、事象、結果/影響 を <ul> リストで綺麗に整理。
       - <b>地銀視点の深掘り</b>: 取引先への影響や顧客との会話ネタを <p> タグで記述。
       - 最後に「続きを読む」というボタン風リンク: <a href="記事URL" role="button" class="outline">続きを読む</a>

    【ニュースリスト】
    {news_text}
    """
    
    response = model.generate_content(prompt)
    html_content = response.text
    
    # AIがMarkdownの ```html 〜 ``` で囲んでしまった場合に取り除く処理
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]
        
    return html_content.strip()

def send_line_message(token, user_id, message):
    url = "[https://api.line.me/v2/bot/message/push](https://api.line.me/v2/bot/message/push)"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {"to": user_id, "messages": [{"type": "text", "text": message}]}
    requests.post(url, headers=headers, data=json.dumps(data))

if __name__ == "__main__":
    news_data = fetch_news(RSS_URLS)
    weather_data = fetch_weather_sapporo()
    
    if news_data:
        # 1. HTMLを生成
        html_output = create_html_news(news_data, weather_data)
        
        # 2. docsフォルダを作って index.html として保存
        os.makedirs("docs", exist_ok=True)
        with open("docs/index.html", "w", encoding="utf-8") as f:
            f.write(html_output)
            
        # 3. LINEにはURLだけを送る (あなたのGitHub IDとリポジトリ名に書き換えてください)
        # 例: GITHUB_ID_HERE を "Taro-Yamada" などにする
        github_id = "あなたのGitHubユーザー名" 
        repo_name = "morning-news-bot"
        site_url = f"https://{github_id}.github.io/{repo_name}/"
        
        line_msg = f"🌤 今日のニュースが更新されました！\nブラウザでサクッと確認してください👇\n{site_url}"
        send_line_message(LINE_ACCESS_TOKEN, LINE_USER_ID, line_msg)
