import requests

NEWS_API_KEY = "a198000045e94de0bb233d9957fbe367"

def get_latest_finance_news(top_n=3):
    """
    Fetch top finance/business news
    """
    url = f"https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize={top_n}&apiKey={NEWS_API_KEY}"
    try:
        resp = requests.get(url).json()
        articles = resp.get("articles", [])
        news_list = []
        for a in articles:
            title = a.get("title", "")
            source = a.get("source", {}).get("name", "")
            news_list.append(f"{title} ({source})")
        return news_list
    except:
        return ["Could not fetch news at this time."]
