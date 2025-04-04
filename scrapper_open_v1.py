from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from dotenv import load_dotenv
import os

from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Scrapper:
    def __init__(self, device="web"):
        self.opts = FirefoxOptions()
        self.opts.add_argument("--headless")
        self.opts.add_argument("--disable-gpu")
        self.opts.add_argument("--no-sandbox")

        geckodriver_path = "./geckodriver"  # Make sure this path is correct
        driver_service = FirefoxService(executable_path=geckodriver_path)
        self.driver = webdriver.Firefox(service=driver_service, options=self.opts)
    def extract_news(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        articles = []

        # List of known article link selectors on crypto/news-like sites
        selectors = [
            'a.home-latest-news__item',
            'a.card-article',
            'a.post-item',
            'a.article-card',
            'a.news-link',
            'a.featured-article',
            'a.entry-title',
            'a.title',
        ]

        for selector in selectors:
            for a in soup.select(selector):
                title = a.get_text(strip=True)
                href = a.get('href', '')
                if title and href and href.startswith("http"):
                    articles.append((title, href))

        # Fallback: get anything that looks like a real article title
        if not articles:
            for a in soup.find_all('a', href=True):
                title = a.get_text(strip=True)
                href = a['href']
                if (
                    title and len(title.split()) > 5 and
                    href.startswith("http") and
                    "tag" not in href and "privacy" not in href and "cookie" not in href
                ):
                    articles.append((title, href))

        # Deduplicate
        seen = set()
        filtered_articles = []
        for title, url in articles:
            if title not in seen:
                seen.add(title)
                filtered_articles.append((title, url))

        return filtered_articles[:40]  # Increased limit for better AI input
  # Top 30 for GPT to summarize
    def extract_full_article(self, url):
        try:
            self.driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Try several common article content containers
            selectors = [
                'div.article-content',     # Crypto.news
                'div.post-content',
                'div.entry-content',
                'div.content',
                'article',
            ]

            for selector in selectors:
                container = soup.select_one(selector)
                if container:
                    text = container.get_text(separator=' ', strip=True)
                    return text[:1000]  # Limit to 1000 characters

            return soup.get_text(separator=' ', strip=True)[:1000]
        except Exception as e:
            print(f"❌ Failed to load article {url}: {e}")
            return ""


    def close(self):
        self.driver.quit()

def run_ai_summary(start_url, goal="Summarize the top crypto news"):
    bot = Scrapper()
    bot.driver.get(start_url)
    time.sleep(3)

    print("🔎 Extracting news headlines...")
    articles = bot.extract_news()

    print("📰 Visiting each article to get summary...")
    enriched_articles = []
    for title, url in articles[:10]:  # Visit only top 10 for speed
        summary = bot.extract_full_article(url)
        enriched_articles.append((title, url, summary))
    
    bot.close()

    combined_text = "\n\n".join(
        [f"{i+1}. {title}\n{summary}\n({url})" for i, (title, url, summary) in enumerate(enriched_articles)]
    )

    prompt = f"""
You are a crypto news analyst. Based on the following detailed articles, summarize the 10 most important ones.

For each, return a **brief headline**, a **summary**, and include the **URL**.

Articles:
{combined_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional crypto news summarizer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    result = run_ai_summary("https://crypto.news/")
    print("\n📰 Top 10 Crypto News:\n")
    print(result)
