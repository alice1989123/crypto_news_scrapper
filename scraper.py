from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone
import boto3
import os
import json
import gzip
import hashlib
from urllib.parse import urlparse


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_source_from_url(url: str) -> str:
    # e.g. crypto.news -> crypto.news
    host = urlparse(url).netloc.lower()
    host = host.replace("www.", "")
    return host or "unknown"


def save_raw_article(base_dir: str, source: str, article_id: str, obj: dict) -> str:
    dt = datetime.now(timezone.utc)
    out_dir = os.path.join(
        base_dir,
        "raw",
        f"year={dt.year}",
        f"month={dt.month:02d}",
        f"day={dt.day:02d}",
        f"source={source}",
    )
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{article_id}.json.gz")

    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    with gzip.open(path, "wb") as f:
        f.write(payload)

    return path


class Scrapper:
    def __init__(self):
        self.opts = Options()
        self.opts.binary_location = "/usr/bin/firefox"
        self.opts.add_argument("--headless")
        self.opts.add_argument("--no-sandbox")
        self.opts.add_argument("--disable-dev-shm-usage")

        driver_service = Service("/usr/local/bin/geckodriver")
        self.driver = webdriver.Firefox(service=driver_service, options=self.opts)

    def extract_news(self):
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        articles = []

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            href = a["href"]

            if (
                title and len(title.split()) > 5
                and href.startswith("http")
                and "tag" not in href
                and "privacy" not in href
                and "cookie" not in href
                and "login" not in href
            ):
                articles.append((title, href))

        # Deduplicate by URL (better than title)
        seen = set()
        filtered = []
        for title, url in articles:
            if url in seen:
                continue
            seen.add(url)
            filtered.append((title, url))

        print("🔗 Found article candidates:", len(filtered))
        for title, url in filtered[:20]:
            print(f"📝 {title} -> {url}")

        return filtered[:40]

    def extract_full_article(self, url):
        try:
            self.driver.get(url)
            time.sleep(2)
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            selectors = [
                "div.article-content",  # crypto.news (sometimes)
                "div.post-content",
                "div.entry-content",
                "div.content",
                "article",
            ]

            for selector in selectors:
                container = soup.select_one(selector)
                if container:
                    text = container.get_text(separator=" ", strip=True)
                    return text  # store full text

            return soup.get_text(separator=" ", strip=True)
        except Exception as e:
            print(f"❌ Failed to load article {url}: {e}")
            return ""

    def close(self):
        self.driver.quit()


def run_scrape_to_queue(start_url: str, limit: int = 10):
    base_dir = os.environ.get("GASTYT_DATA_DIR", "/data/gatsbyt")
    queue_url = os.environ["QUEUE_URL"]
    region = os.getenv("AWS_DEFAULT_REGION", "mx-central-1")

    # Ensure base dirs exist
    os.makedirs(os.path.join(base_dir, "raw"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "summaries"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)

    sqs = boto3.client("sqs", region_name=region)

    bot = Scrapper()
    bot.driver.get(start_url)
    time.sleep(3)

    print("🔎 Extracting news headlines...")
    articles = bot.extract_news()

    print("📰 Visiting each article to extract text + enqueue pointer jobs...")
    for i, (title, url) in enumerate(articles[:limit], start=1):
        source = safe_source_from_url(url)
        article_id = sha256(url)
        extracted_at = datetime.now(timezone.utc).isoformat()

        # Idempotency: if raw file already exists, skip re-writing and re-queueing
        # (You can remove this if you want to always enqueue)
        raw_path_guess = os.path.join(
            base_dir,
            "raw",
            f"year={datetime.now(timezone.utc).year}",
            f"month={datetime.now(timezone.utc).month:02d}",
            f"day={datetime.now(timezone.utc).day:02d}",
            f"source={source}",
            f"{article_id}.json.gz",
        )
        if os.path.exists(raw_path_guess):
            print(f"↩️  [{i}/{limit}] raw already exists, skipping: {url}")
            continue

        text = bot.extract_full_article(url)
        if len(text) < 400:
            print(f"⚠️  [{i}/{limit}] too little text, skipping: {url}")
            continue

        raw_obj = {
            "article_id": article_id,
            "source": source,
            "title": title,
            "url": url,
            "extracted_at": extracted_at,
            "text": text,
        }

        raw_path = save_raw_article(base_dir, source, article_id, raw_obj)

        msg = {
            "job": "summarize_article",
            "article_id": article_id,
            "source": source,
            "title": title,
            "url": url,
            "path": raw_path,
            "extracted_at": extracted_at,
        }

        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(msg))
        print(f"✅ [{i}/{limit}] saved + queued -> {raw_path}")

    bot.close()


if __name__ == "__main__":
    limit=os.getenv("SCRAPE_LIMIT")
    if limit is not None:
        limit = int(limit)
    else:
        limit = 10
    run_scrape_to_queue("https://crypto.news/", limit)
