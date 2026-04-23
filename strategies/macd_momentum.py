from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
import numpy as np

class MacdMomentumStrategy(Strategy):
    def __init__(self):
        self.fast = 12
        self.slow = 26
        self.signal = 9

    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty or len(data) < self.slow + self.signal:
            return 'HOLD', 0.0
        
        # Calculate MACD
        exp1 = data['Close'].ewm(span=self.fast, adjust=False).mean()
        exp2 = data['Close'].ewm(span=self.slow, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['Signal'] = data['MACD'].ewm(span=self.signal, adjust=False).mean()
        
        close = float(data['Close'].iloc[-1])
        macd = float(data['MACD'].iloc[-1])
        signal = float(data['Signal'].iloc[-1])
        prev_macd = float(data['MACD'].iloc[-2])
        prev_signal = float(data['Signal'].iloc[-2])
        
        if np.isnan(macd) or np.isnan(signal):
            return 'HOLD', close

        # Strategy Logic: Crossover
        # Buy when MACD crosses above Signal
        if prev_macd <= prev_signal and macd > signal and not current_position:
            return 'BUY', close
        # Sell when MACD crosses below Signal
        elif prev_macd >= prev_signal and macd < signal and current_position:
            return 'SELL', close
        else:
            return 'HOLD', close
