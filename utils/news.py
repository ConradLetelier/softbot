import yfinance as yf
from datetime import datetime
import pandas as pd

def fetch_ticker_news(ticker_symbol):
    """Fetch raw news items for a specific ticker using yfinance."""
    try:
        t = yf.Ticker(ticker_symbol)
        return t.news or []
    except Exception:
        return []

def process_news_item(item):
    """Extracts and cleans a news item from yfinance's nested structure."""
    # Handle both new nested structure and old flat structure
    content = item.get('content', item)
    
    # Extract URL
    url = content.get('clickThroughUrl', {}).get('url') or content.get('link')
    if not url:
        return None
    
    # Extract Title
    title = content.get('title')
    if not title:
        return None
    
    # Extract Publisher
    publisher = content.get('provider', {}).get('displayName') or content.get('publisher', 'Finance News')
    
    # Extract and Parse Timestamp
    ts_raw = content.get('pubDate') or content.get('providerPublishTime')
    ts = 0
    time_str = "Recent"
    
    try:
        dt_obj = None
        if isinstance(ts_raw, str):
            # Parse ISO format "2026-03-15T00:16:54Z"
            dt_obj = datetime.strptime(ts_raw.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
            ts = dt_obj.timestamp()
        elif isinstance(ts_raw, (int, float)):
            dt_obj = datetime.fromtimestamp(ts_raw)
            ts = ts_raw
        
        if dt_obj:
            now = datetime.now()
            if dt_obj.date() == now.date():
                time_str = dt_obj.strftime('%H:%M')
            else:
                time_str = dt_obj.strftime('%b %d')
    except Exception:
        pass

    return {
        "time": time_str,
        "timestamp": ts,
        "text": title,
        "url": url,
        "publisher": publisher
    }

def get_live_news_list(tickers, limit=20):
    """Fetch and process live news for a list of tickers."""
    all_news = []
    seen_urls = set()
    
    # Add major ones to ensure variety if list is short
    extended_tickers = list(tickers)
    if "^OMX" not in extended_tickers: extended_tickers.append("^OMX")
    
    for symbol in extended_tickers:
        raw_news = fetch_ticker_news(symbol)
        for item in raw_news:
            processed = process_news_item(item)
            if processed and processed['url'] not in seen_urls:
                all_news.append(processed)
                seen_urls.add(processed['url'])
                
    # Sort by timestamp descending
    all_news.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_news[:limit]
