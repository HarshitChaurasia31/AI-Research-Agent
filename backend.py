from fastapi import FastAPI
import os
import requests
from newspaper import Article
import concurrent.futures

app = FastAPI(title="AI Research Agent Backend")

@app.get("/")
def read_root():
    return {"message": "AI Research Agent Backend is running"}

@app.post("/search")
def search_articles(topic: str, tone: str = "Formal", language: str = "English", time_filter: str = "All time"):
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_api_key:
        return {"error": "SERPAPI_API_KEY not set"}

    language_map = {"English": "en", "Spanish": "es", "German": "de","Hindi":"hi"}
    time_map = {"All time": None, "Past year": "y", "Past month": "m"}

    params = {
        "engine": "google",
        "q": topic,
        "api_key": serpapi_api_key,
        "hl": language_map[language]
    }
    if time_map[time_filter]:
        params["tbs"] = f"qdr:{time_map[time_filter]}"

    try:
        search_results = requests.get("https://serpapi.com/search.json", params=params).json()
    except Exception as e:
        return {"error": str(e)}

    if "organic_results" not in search_results:
        return {"error": "No results found"}

    def fetch_article(result):
        url = result.get("link", "")
        title = result.get("title", "")
        if not url:
            return None
        try:
            article = Article(url)
            article.download()
            article.parse()
            author = ", ".join(article.authors) if article.authors else "Unknown"
            publish_date = article.publish_date.strftime("%Y-%m-%d") if article.publish_date else "Unknown"
            domain = article.source_url if article.source_url else url.split("/")[2]
            content = "\n".join(article.text.split("\n")[:5])
            return {
                "title": title,
                "author": author,
                "date": publish_date,
                "domain": domain,
                "url": url,
                "content": content
            }
        except:
            return None

    results_to_fetch = search_results.get("organic_results", [])[:5]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        fetched_articles = list(executor.map(fetch_article, results_to_fetch))

    sources_info = [art for art in fetched_articles if art]

    return {"articles": sources_info}
