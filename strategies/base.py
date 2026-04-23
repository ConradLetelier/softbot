from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Any, Dict
import pandas as pd

class Strategy(ABC):
    @abstractmethod
    def generate_signal(
        self, 
        ticker: str, 
        data: pd.DataFrame, 
        news: Optional[List[Any]] = None, 
        current_position: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, float]:
        """Returns 'BUY', 'SELL', or 'HOLD' along with the current price."""
        pass
