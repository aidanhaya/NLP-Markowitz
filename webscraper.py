from bs4 import BeautifulSoup
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

LISTING_URL = "https://www.fool.com/earnings-call-transcripts/"

def scrape_motley_fool_transcript(ticker: str):
    with sync_playwright() as p: # opens a playwright session
        # launches real Chromium browser
        browser = p.chromium.launch(headless=True) # set to false to show visible window
        # opens Chromium browser tab
        page = browser.new_page()

        # Step 1: Fetch the listing page and wait for JS to render links
        page.goto(LISTING_URL, timeout=60000) # navigates to url, wait 60000ms = 60s
        # pauses execution until a DOM element matching the CSS selector appears
        page.wait_for_selector("a[href*='/earnings/call-transcripts/']", timeout=30000)
        # BeautifulSoup object containing HTML page content
        soup = BeautifulSoup(page.content(), "html.parser")

        # Step 2: Find a transcript link containing the ticker
        links = soup.find_all("a", href=True)
        all_transcript_links = [
            l["href"] for l in links
            if "/earnings/call-transcripts/" in l["href"]
        ]
        print(f"Total transcript links found: {len(all_transcript_links)}")

        transcript_links = [
            l for l in all_transcript_links
            if ticker.lower() in l.lower()
        ]

        if not transcript_links:
            print(f"No transcript found for {ticker}")
            browser.close()
            return None

        # Step 3: Fetch the transcript page
        transcript_url = "https://www.fool.com" + str(transcript_links[0])
        page.goto(transcript_url, timeout=60000)
        page.wait_for_selector("div.article-body", timeout=30000)
        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()

        # Step 4: Extract article body
        article = soup.find("div", class_="article-body")
        if not article:
            return None

        paragraphs = [p.get_text(strip=True) for p in article.find_all("p")]
        full_text = "\n".join(paragraphs)

        date_tag = soup.find("time")

        if date_tag:
            date = date_tag.get("datetime") or date_tag.get_text(strip=True)
        else:
            date = str(datetime.today().date())

        return {
            "ticker": ticker,
            "url": transcript_url,
            "date": date,
            "text": full_text,
        }


def scrape_universe(tickers: list, delay: float = 2.0):
    results = {}
    for ticker in tickers:
        print(f"Scraping {ticker}...")
        result = scrape_motley_fool_transcript(ticker)
        if result:
            results[ticker] = result
        time.sleep(delay)
    return results