import webscraper as ws
import preprocessing as pp
import sentiment_scoring as scr

def main():
    results = ws.scrape_all_transcripts()
    tickers_list = list(results.keys())
    scorer = scr.FinBERTScorer()

    for i, ticker in enumerate(tickers_list):
        print(f">> {i} - {ticker}")

        split_text = pp.split_transcript(results[ticker]['text'])
        cleaned_text = {"prepared": pp.clean_text(split_text["prepared"]),
                        "qa": pp.clean_text(split_text["qa"])}
        tokenized_text = {"prepared": pp.sentence_tokenize(cleaned_text["prepared"]),
                          "qa": pp.sentence_tokenize(cleaned_text["qa"])}

        scores = scr.score_transcript(tokenized_text, ticker, results[ticker]["date"], scorer)

        print(f"Prepared score: {scores['prepared']}\nQA score: {scores['qa']}"
              f"\nComposite score: {scores['composite']}")

if __name__ == "__main__":
    main()