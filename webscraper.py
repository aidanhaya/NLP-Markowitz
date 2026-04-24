from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

LISTING_PAGES = [
    "https://www.fool.com/earnings-call-transcripts/",
    "https://www.fool.com/earnings-call-transcripts/page/2/",
]

def scrape_all_transcripts(delay: float = 2.0) -> dict:
    results = {}
    today = str(datetime.today().date())  # e.g. "2026-04-24"

    with sync_playwright() as p: # opens a playwright session
        # launches real Chromium browser
        browser = p.chromium.launch(headless=True) # set to false to show visible window
        # opens Chromium browser tab
        page = browser.new_page()

        # Step 1: Collect transcript links from both listing pages
        pattern = re.compile(
            r"/earnings/call-transcripts/\d{4}/\d{2}/\d{2}/"  # date path
            r"(?:[a-z0-9]+-)*"  # company name slug (non-capturing)
            r"([A-Z]{1,5}|[a-z]{1,5})"  # ticker capture group
            r"-q[1-4]-\d{4}"  # quarter + year
            r"-earnings(?:-call)?-transcript/"  # either format
        )
        date_pattern = re.compile(r"/earnings/call-transcripts/(\d{4})/(\d{2})/(\d{2})/")
        seen_tickers = set()
        ticker_href_pairs = []

        for listing_url in LISTING_PAGES:
            page.goto(listing_url, timeout=60000)
            page.wait_for_selector("a[href*='/earnings/call-transcripts/']", timeout=30000)
            soup = BeautifulSoup(page.content(), "html.parser")

            for l in soup.find_all("a", href=True):
                href = l["href"]
                if "/earnings/call-transcripts/" not in href:
                    continue
                match = pattern.search(href)
                if not match:
                    continue
                ticker = match.group(1).lower()
                if ticker in seen_tickers:
                    continue
                # filter to today's transcripts only using the date in the URL
                date_match = date_pattern.search(href)
                if date_match:
                    link_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                    if link_date != today:
                        continue
                seen_tickers.add(ticker)
                ticker_href_pairs.append((ticker, href))

        print(f"Found {len(ticker_href_pairs)} tickers from today ({today}): {[t for t, _ in ticker_href_pairs]}")

        # Step 2: Visit each transcript page in the same browser session
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