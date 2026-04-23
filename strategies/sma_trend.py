from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd

class SmaTrendStrategy(Strategy):
    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty or len(data) < 200:
            return 'HOLD', 0.0
        
        # Calculate SMA
        data['SMA50'] = data['Close'].rolling(window=50).mean()
        data['SMA200'] = data['Close'].rolling(window=200).mean()
        
        close = float(data['Close'].iloc[-1])
        sma50 = float(data['SMA50'].iloc[-1])
        sma200 = float(data['SMA200'].iloc[-1])
        
        # Strategy Logic
        if close > sma50 and sma50 > sma200:
            return 'BUY', close
        elif close < sma50:
            return 'SELL', close
        else:
            return 'HOLD', close
