from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
import numpy as np

class RsiReversionStrategy(Strategy):
    def __init__(self):
        self.period = 14
        self.oversold = 30
        self.overbought = 65

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty or len(data) < self.period + 5:
            return 'HOLD', 0.0
        
        data['RSI'] = self.calculate_rsi(data['Close'], self.period)
        
        close = float(data['Close'].iloc[-1])
        rsi = float(data['RSI'].iloc[-1])
        
        if np.isnan(rsi):
            return 'HOLD', close

        # Strategy Logic
        if rsi < self.oversold and not current_position:
            return 'BUY', close
        elif rsi > self.overbought and current_position:
            return 'SELL', close
        else:
            return 'HOLD', close
