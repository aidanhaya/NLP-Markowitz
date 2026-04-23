import webscraper as ws

def main():
    results = ws.scrape_all_transcripts()

    tickers_list = list(results.keys())
    for i, ticker in enumerate(tickers_list):
        print(f">> {i} - {results[ticker]['ticker']}")
        print(results[ticker]["text"][:500])

if __name__ == "__main__":
    main()