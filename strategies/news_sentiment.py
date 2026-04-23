from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
from datetime import datetime, time as dtime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class NewsSentimentStrategy(Strategy):
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.buy_threshold = 0.15
        self.sell_threshold = 0.05
        self.stop_loss_pct = 0.05
        self.trailing_stop_pct = 0.03
        self.eod_exit_time = None # Disabled to allow overnight swings

    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None,
        current_time: Optional[dtime] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty:
            return 'HOLD', 0.0
        
        current_price = float(data['Close'].iloc[-1])
        now_time = current_time or datetime.now().time()

        # 1. Check for Stops if we have a position
        if current_position:
            buy_price = current_position.get('buy_price')
            high_price = current_position.get('high_price', buy_price)
            
            # Hard Stop-Loss
            if buy_price:
                price_change = (current_price / buy_price) - 1
                if price_change <= -self.stop_loss_pct:
                    return 'SELL', current_price
            
            # Trailing Stop-Loss (2% from the peak)
            if high_price and current_price < (high_price * (1 - self.trailing_stop_pct)):
                return 'SELL', current_price

        # 3. Analyze Sentiment if news available
        if news:
            scores = []
            for item in news:
                title = item.get('title') or item.get('text')
                if title:
                    sentiment = self.analyzer.polarity_scores(title)
                    scores.append(sentiment['compound'])
            
            if len(scores) >= 1:
                avg_sentiment = sum(scores) / len(scores)
                
                # Logic for BUY
                if not current_position and avg_sentiment >= self.buy_threshold:
                    return 'BUY', current_price
                
                # Logic for SELL (Sentiment reversal)
                if current_position and avg_sentiment < self.sell_threshold:
                    return 'SELL', current_price

        return 'HOLD', current_price
