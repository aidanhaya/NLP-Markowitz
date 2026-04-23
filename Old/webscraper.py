from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

LISTING_URL = "https://www.fool.com/earnings-call-transcripts/"

def scrape_all_transcripts(delay: float = 2.0):
    """
    Single-session scrape: fetch the listing page once, extract all tickers and
    their transcript links, then visit each transcript page in the same browser.
    """
    results = {}

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
        # regex expression to extract transcript hyperlinks and isolate tickers
        pattern = re.compile(r"/earnings/call-transcripts/\d{4}/\d{2}/\d{2}/([a-zA-Z]+)-")

        seen_tickers = set()

        ticker_href_pairs = []

        # runs through all found hyperlinks and only selects those with found tickers
        for l in links:
            href = l["href"]
            # checks if hyperlink is a transcript
            if "/earnings/call-transcripts/" not in href:
                continue
            # tries to match hyperlinks to extracted regex pattern
            match = pattern.search(href)
            if match:
                ticker = match.group(1).lower() # extracts ticker (inside parentheses)
                if ticker not in seen_tickers:
                    seen_tickers.add(ticker)
                    ticker_href_pairs.append((ticker, href))

        print(f"Found {len(ticker_href_pairs)} tickers: {[t for t, _ in ticker_href_pairs]}")

        # Step 3: Visit each transcript page in the same browser session
        for ticker, href in ticker_href_pairs:
            print(f"Scraping {ticker}...")
            try:
                transcript_url = "https://www.fool.com" + href
                page.goto(transcript_url, timeout=60000)
                page.wait_for_selector("div.article-body", timeout=30000)
                soup = BeautifulSoup(page.content(), "html.parser")

                # extracts text under "article-body" div
                article = soup.find("div", class_="article-body")
                if not article:
                    print(f" > No article body found for {ticker}, skipping.")
                    continue

                paragraphs = [p.get_text(strip=True) for p in article.find_all("p")]
                full_text = "\n".join(paragraphs)

                date_tag = soup.find("time")
                if date_tag:
                    date = date_tag.get("datetime") or date_tag.get_text(strip=True)
                else:
                    date = str(datetime.today().date())

                results[ticker] = {
                    "ticker": ticker,
                    "url": transcript_url,
                    "date": date,
                    "text": full_text,
                }

            # handles 404 errors, browser crashes, no "article-body" div, etc
            except Exception as e:
                print(f" > Error scraping {ticker}: {e}")

            time.sleep(delay)

        browser.close()

    return results