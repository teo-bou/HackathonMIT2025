from ddgs import DDGS
import trafilatura

def fetch_article_text(url):
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        return trafilatura.extract(downloaded)
    return None

def search_and_scrape(query="latest trends online Tiktok", max_results=3):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="wt-wt", safesearch="off", max_results=max_results):
            url = r['href']
            title = r['title']
            content = fetch_article_text(url)
            if content:
                results.append(f"### {title}\n{content}\nURL: {url}\n")
    return "\n".join(results)