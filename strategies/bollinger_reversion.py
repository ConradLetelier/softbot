from .base import Strategy
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd
import numpy as np

class BollingerReversionStrategy(Strategy):
    def __init__(self):
        self.window = 20
        self.num_std = 2

    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        if data is None or data.empty or len(data) < self.window:
            return 'HOLD', 0.0
        
        # Calculate Bollinger Bands
        data['MA20'] = data['Close'].rolling(window=self.window).mean()
        data['STD20'] = data['Close'].rolling(window=self.window).std()
        data['Upper'] = data['MA20'] + (data['STD20'] * self.num_std)
        data['Lower'] = data['MA20'] - (data['STD20'] * self.num_std)
        
        close = float(data['Close'].iloc[-1])
        lower = float(data['Lower'].iloc[-1])
        upper = float(data['Upper'].iloc[-1])
        ma = float(data['MA20'].iloc[-1])
        
        if np.isnan(lower):
            return 'HOLD', close

        # Strategy Logic
        if close <= lower and not current_position:
            return 'BUY', close
        elif close >= ma and current_position: # Exit at Mean or Upper
            return 'SELL', close
        else:
            return 'HOLD', close
