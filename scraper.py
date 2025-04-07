from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
import time
from model_runner import call_llm
from datetime import datetime
import boto3
import os
import json


class Scrapper:
    def __init__(self):
        self.opts = Options()
        self.opts.binary_location = "/opt/firefox/firefox"  # 👈 This is the correct way now
        self.opts.add_argument("--headless")
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument("--disable-dev-shm-usage")

        driver_service = Service("/usr/local/bin/geckodriver")
        self.driver = webdriver.Firefox(service=driver_service, options=self.opts)

   


    def extract_news(self):
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        articles = []

        # Grab ALL <a> tags with hrefs that look like article links
        for a in soup.find_all('a', href=True):
            title = a.get_text(strip=True)
            href = a['href']
            if (
                title and len(title.split()) > 5 and
                href.startswith("http") and
                "tag" not in href and
                "privacy" not in href and
                "cookie" not in href and
                "login" not in href
            ):
                articles.append((title, href))

        # Deduplicate
        seen = set()
        filtered_articles = []
        for title, url in articles:
            if title not in seen:
                seen.add(title)
                filtered_articles.append((title, url))
        print("🔗 Found article candidates:")
        for title, url in filtered_articles:
            print(f"📝 {title} -> {url}")
        

        return filtered_articles[:40] # Increased limit for better AI input
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

def run_ai_summary(start_url):
    bot = Scrapper()
    bot.driver.get(start_url)
    time.sleep(3)

    print("🔎 Extracting news headlines...")
    articles = bot.extract_news()

    # 📨 SQS client
    sqs = boto3.client('sqs', region_name='eu-central-1')
    queue_url = os.environ['QUEUE_URL']  # set this via env or pass it in

    print("📰 Visiting each article to get summaries individually...")
    for i, (title, url) in enumerate(articles[:10]):
        content = bot.extract_full_article(url)

        prompt = f"""
            You are a crypto news summarizer. Summarize the following article clearly and briefly.

            Title: {title}

            Content:
            {content}

            Return the output as:
            - Headline: ...
            - Summary: ...
            - URL: {url}
        """

        response = call_llm(prompt)
        timestamp = datetime.now().isoformat()
        message_body = {
            "headline": title,
            "summary": response,
            "url": url,
            "timestamp": timestamp
        }

        # 🔥 Send to SQS
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body)
        )

        print(f"✅ [{i+1}/10] summarized and sent to queue")

    bot.close()


if __name__ == "__main__":
    run_ai_summary("https://crypto.news/")