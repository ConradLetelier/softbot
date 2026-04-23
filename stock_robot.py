import yfinance as yf
import pandas as pd
import math
import schedule
import json
import time
import os
import importlib
import argparse
import logging
import sys
from datetime import datetime, time as dtime
from utils.news_tracker import is_news_processed, mark_news_as_processed

# --- LOGGING SETUP ---
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("data/robot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- CONFIGURATION & FILES ---
CONFIG_FILE = "config.json"
PORTFOLIO_FILE = "portfolio.json"
HISTORY_FILE = "data/equity_history.json"

class ConfigManager:
    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_FILE):
            default_config = {
                "auto_run": True,
                "run_time": "17:15",
                "starting_capital": 5000,
                "commission_pct": 0.0025,
                "commission_min": 1.0,
                "active_strategies": ["sma_trend", "news_sentiment"],
                "tickers": ["VOLV-B.ST", "INVE-B.ST", "SEB-A.ST"]
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            return default_config
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

class PortfolioManager:
    def __init__(self, config, strategy_id):
        self.strategy_id = strategy_id
        self.max_slots = 5
        self.initial_capital = config.get("starting_capital", 5000)
        self.commission_pct = config.get("commission_pct", 0.0025)
        self.commission_min = config.get("commission_min", 1.0)
        self.slot_budget = self.initial_capital / self.max_slots
        self.load_portfolio()

    def load_portfolio(self):
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                all_portfolios = json.load(f)
                strategy_data = all_portfolios.get(self.strategy_id, {})
                self.cash = strategy_data.get("cash", self.initial_capital)
                self.positions = strategy_data.get("positions", {})
        else:
            self.cash = self.initial_capital
            self.positions = {}

    def save_portfolio(self):
        all_portfolios = {}
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                all_portfolios = json.load(f)
        
        all_portfolios[self.strategy_id] = {
            "cash": self.cash,
            "positions": self.positions
        }
        
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(all_portfolios, f, indent=4)
        self.log_equity()

    def log_equity(self):
        """Saves total market value for history tracking."""
        current_value = self.cash
        
        # Fetch live prices for accuracy in history
        if self.positions:
            tickers = list(self.positions.keys())
            try:
                data = yf.download(tickers, period="5d", interval="1m", progress=False)
                if data is not None and not data.empty:
                    for ticker, pos in self.positions.items():
                        try:
                            if len(tickers) > 1:
                                price_series = data['Close'][ticker]
                            else:
                                price_series = data['Close']
                            
                            if isinstance(price_series, pd.Series):
                                valid_prices = price_series.dropna()
                                if not valid_prices.empty:
                                    price = float(valid_prices.values[-1])
                                    current_value += pos['shares'] * price
                                else:
                                    current_value += pos['shares'] * pos['buy_price']
                            else:
                                # Fallback for other data types (like numpy arrays)
                                try:
                                    price = float(price_series[-1])
                                    current_value += pos['shares'] * price
                                except Exception:
                                    current_value += pos['shares'] * pos['buy_price']
                        except Exception:
                            current_value += pos['shares'] * pos['buy_price']
            except Exception as e:
                logging.warning(f"[!] Warning: Could not fetch live prices for history log ({e}). Using buy price.")
                for ticker, pos in self.positions.items():
                    current_value += pos['shares'] * pos['buy_price']
            
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        
        history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "strategy": self.strategy_id,
            "value": round(current_value, 2)
        })
        
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)

    def calculate_commission(self, amount):
        return max(self.commission_min, amount * self.commission_pct)

    def execute_buy(self, ticker, price):
        if len(self.positions) >= self.max_slots: return False, "Full"
        if ticker in self.positions: return False, "Already owned"
        
        num_shares = math.floor(self.slot_budget / (price * (1 + self.commission_pct)))
        trade_amount = num_shares * price
        comm = self.calculate_commission(trade_amount)
        if num_shares > 0 and self.cash >= (trade_amount + comm):
            self.cash -= (trade_amount + comm)
            self.positions[ticker] = {
                "shares": num_shares, 
                "buy_price": price,
                "high_price": price,
                "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.save_portfolio()
            return True, f"BOUGHT {num_shares} {ticker}"
        return False, "Insufficient capital"

    def update_high_price(self, ticker, price):
        """Updates the highest price seen since purchase for trailing stop calculation."""
        if ticker in self.positions:
            old_high = self.positions[ticker].get("high_price", 0)
            if price > old_high:
                self.positions[ticker]["high_price"] = price
                self.save_portfolio()
                return True
        return False

    def execute_sell(self, ticker, price):
        if ticker in self.positions:
            pos = self.positions.pop(ticker)
            trade_amount = pos['shares'] * price
            comm = self.calculate_commission(trade_amount)
            self.cash += (trade_amount - comm)
            self.save_portfolio()
            return True, f"SOLD {ticker}"
        return False, "Not owned"

class TradingEngine:
    def __init__(self):
        self.config = ConfigManager.load_config()
        self.strategies = self._load_strategies()

    def _load_strategies(self):
        """Dynamically loads strategy classes and pairs them with their portfolios."""
        active_strats = self.config.get("active_strategies", ["sma_trend"])
        strategy_instances = []
        
        for strat_id in active_strats:
            try:
                module_name = f"strategies.{strat_id}"
                module = importlib.import_module(module_name)
                class_name = "".join(x.capitalize() for x in strat_id.split("_")) + "Strategy"
                strategy_class = getattr(module, class_name)
                
                strategy_instances.append({
                    "id": strat_id,
                    "logic": strategy_class(),
                    "portfolio": PortfolioManager(self.config, strat_id)
                })
                logging.info(f"[*] Loaded strategy: {strat_id}")
            except Exception as e:
                logging.error(f"[!] Failed to load strategy {strat_id}: {e}")
        
        return strategy_instances

    def is_market_open(self):
        """Checks if the Swedish stock market is currently open (approx 09:00 - 17:30)."""
        now = datetime.now()
        # Monday is 0, Sunday is 6
        if now.weekday() >= 5:
            return False
        
        market_start = dtime(9, 0)
        market_end = dtime(17, 30)
        return market_start <= now.time() <= market_end

    def run_daily_analysis(self, force=False):
        """Runs technical analysis (SMA) at market close."""
        if not force and not self.is_market_open():
            return

        logging.info(f"[*] Starting daily technical analysis...")
        tickers = self.config["tickers"]
        
        # Only run technical strategies (like sma_trend)
        daily_strats = [s for s in self.strategies if s["id"] != "news_sentiment"]

        for ticker in tickers:
            try:
                t_obj = yf.Ticker(ticker)
                df = t_obj.history(period="2y")
                
                for strat in daily_strats:
                    strat_id = strat["id"]
                    logic = strat["logic"]
                    portfolio = strat["portfolio"]
                    current_pos = portfolio.positions.get(ticker)
                    
                    signal, price = logic.generate_signal(ticker, df, current_position=current_pos)
                    
                    if signal == 'SELL':
                        success, msg = portfolio.execute_sell(ticker, price)
                        if success: logging.info(f"[-] [{strat_id}] {msg}")
                    elif signal == 'BUY':
                        success, msg = portfolio.execute_buy(ticker, price)
                        if success: logging.info(f"[+] [{strat_id}] {msg}")
                        
            except Exception as e:
                logging.error(f"[!] Error on {ticker} (Daily): {e}")
        
        logging.info("[*] Daily analysis complete.")

    def run_live_news(self, force=False):
        """Polls for new news and triggers news_sentiment strategy during market hours."""
        if not self.config:
            return
            
        if not force and not self.is_market_open():
            return

        logging.info(f"[*] Checking for live news...")
        tickers = self.config.get("tickers", [])
        news_strat = next((s for s in self.strategies if s["id"] == "news_sentiment"), None)
        
        if not news_strat:
            return

        for ticker in tickers:
            try:
                t_obj = yf.Ticker(ticker)
                
                # Get latest price (more robust handling)
                df = t_obj.history(period="1d")
                if df.empty or 'Close' not in df.columns:
                    continue
                
                # Handle potential MultiIndex and extract last price
                close_data = df['Close']
                if isinstance(close_data, pd.DataFrame):
                    # If it's a DataFrame (e.g. MultiIndex), take the first column's last value
                    current_price = float(close_data.iloc[-1, 0])
                else:
                    # If it's a Series, take the last value
                    current_price = float(close_data.iloc[-1])
                
                logic = news_strat["logic"]
                portfolio = news_strat["portfolio"]
                current_pos = portfolio.positions.get(ticker)
                
                # Update high_price for trailing stop logic
                if current_pos:
                    portfolio.update_high_price(ticker, current_price)

                raw_news = t_obj.news or []
                
                # Filter for UNPROCESSED news only
                new_news = []
                for item in raw_news:
                    if not isinstance(item, dict):
                        continue
                        
                    # Safely extract URL
                    url = item.get('link')
                    if not url:
                        ct_url = item.get('clickThroughUrl')
                        if isinstance(ct_url, dict):
                            url = ct_url.get('url')
                    
                    if url and not is_news_processed(url):
                        new_news.append(item)
                        mark_news_as_processed(url)

                # Call strategy (either for new news BUY or for Trailing/EOD SELL)
                signal, price = logic.generate_signal(
                    ticker, df, news=new_news, 
                    current_position=current_pos,
                    current_time=datetime.now().time()
                )
                
                if signal == 'SELL':
                    success, msg = portfolio.execute_sell(ticker, price)
                    if success: logging.info(f"[-] [news_sentiment] {msg}")
                elif signal == 'BUY' and new_news: # Only buy if there's actually a news trigger
                    success, msg = portfolio.execute_buy(ticker, price)
                    if success: logging.info(f"[+] [news_sentiment] {msg}")
                        
            except Exception as e:
                logging.error(f"[!] Error on {ticker} (Live News): {e}")

    def start_scheduler(self):
        run_time = self.config["run_time"]
        
        # Schedule SMA Analysis
        for day in [schedule.every().monday, schedule.every().tuesday, schedule.every().wednesday, 
                    schedule.every().thursday, schedule.every().friday]:
            day.at(run_time).do(self.run_daily_analysis)

        # Schedule Live News Polling (every 2 minutes during market hours)
        schedule.every(2).minutes.do(self.run_live_news)

        logging.info(f"[*] Engine started.")
        logging.info(f"[*] Scheduled: Daily analysis at {run_time}.")
        logging.info(f"[*] Monitoring: Live news every 2 minutes.")
        
        last_heartbeat = 0
        try:
            while True:
                try:
                    schedule.run_pending()
                    
                    # Heartbeat every hour to logs
                    if time.time() - last_heartbeat > 3600:
                        logging.info("[*] Heartbeat: Robot engine is running...")
                        last_heartbeat = time.time()
                        
                    time.sleep(30)
                except Exception as e:
                    logging.error(f"[!] Critical Error in scheduler loop: {e}")
                    time.sleep(60) # Wait before retry
        except KeyboardInterrupt:
            logging.info("Exiting...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stockholm Quant Trading Robot")
    parser.add_argument('--now', action='store_true', help="Run the analysis immediately")
    args = parser.parse_args()

    engine = TradingEngine()
    if args.now:
        engine.run_daily_analysis(force=True)
        engine.run_live_news(force=True)
    else:
        engine.start_scheduler()
