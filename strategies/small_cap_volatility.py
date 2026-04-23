from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
import numpy as np

class SmallCapVolatilityStrategy(Strategy):
    def __init__(self):
        self.lookback = 20
        self.volume_factor = 1.5
        self.trailing_stop_pct = 0.05
        self.hard_stop_pct = 0.08

    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty or len(data) < self.lookback + 5:
            return 'HOLD', 0.0
        
        close = float(data['Close'].iloc[-1])
        volume = float(data['Volume'].iloc[-1])
        avg_volume = float(data['Volume'].tail(10).mean())
        recent_high = float(data['High'].tail(self.lookback).iloc[:-1].max())
        
        # 1. Manage existing position (Aggressive Exit)
        if current_position:
            buy_price = current_position.get('buy_price')
            high_price = current_position.get('high_price', buy_price)
            
            # Hard Stop
            if close < buy_price * (1 - self.hard_stop_pct):
                return 'SELL', close
            
            # Tight Trailing Stop
            if close < high_price * (1 - self.trailing_stop_pct):
                return 'SELL', close
            
            # Take Profit if it hits 15% gain quickly
            if close > buy_price * 1.15:
                return 'SELL', close

        # 2. Buy Signal (Breakout with Volume)
        if not current_position:
            if close > recent_high and volume > (avg_volume * self.volume_factor):
                return 'BUY', close
                
        return 'HOLD', close
