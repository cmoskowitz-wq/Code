"""
workers.py — Background QThread workers so the UI never blocks.
"""
from __future__ import annotations

import requests
import yfinance as yf
from textblob import TextBlob
from PyQt6.QtCore import QThread, pyqtSignal

from analysis import compute_indicators


class MarketDataWorker(QThread):
    """Fetch and compute indicators for a list of symbols off the main thread."""

    data_ready = pyqtSignal(str, object)   # (symbol, DataFrame)
    all_done   = pyqtSignal()
    error      = pyqtSignal(str, str)      # (symbol, message)

    def __init__(self, symbols: list[str]):
        super().__init__()
        self.symbols = list(symbols)

    def run(self) -> None:
        for symbol in self.symbols:
            try:
                df = yf.Ticker(symbol).history(period="3mo")
                if df.empty:
                    self.error.emit(symbol, "No data returned")
                    continue
                df = compute_indicators(df)
                self.data_ready.emit(symbol, df)
            except Exception as exc:
                self.error.emit(symbol, str(exc))
        self.all_done.emit()


class NewsWorker(QThread):
    """Fetch recent news articles for a single symbol, with TextBlob sentiment."""

    articles_ready = pyqtSignal(list)

    def __init__(self, symbol: str, api_key: str):
        super().__init__()
        self.symbol = symbol
        self.api_key = api_key

    def run(self) -> None:
        try:
            url = (
                "https://newsapi.org/v2/everything"
                f"?q={self.symbol}&language=en"
                "&sortBy=publishedAt&pageSize=8"
                f"&apiKey={self.api_key}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            for article in articles:
                title = article.get("title") or ""
                article["_sentiment"] = TextBlob(title).sentiment.polarity
            self.articles_ready.emit(articles)
        except Exception:
            self.articles_ready.emit([])
