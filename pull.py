import webscraper as ws

def main():
    tickers_list = ["aapl", "banc", "uvsp"]
    results = ws.scrape_universe(tickers_list)

    print(results["banc"]["text"])

if __name__ == "__main__":
    main()