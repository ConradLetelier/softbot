import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

STRATEGY_INFO = {
    "sma_trend": "Trend-following strategy that buys when the price is above its 50-day SMA, and the 50-day SMA is above the 200-day SMA. Exits when price drops below SMA 50.",
    "news_sentiment": "Sentiment-based strategy that analyzes recent news headlines. Buys when average sentiment is positive (>0.15) and uses a trailing stop to lock in profits.",
    "rsi_reversion": "Mean-reversion strategy using the Relative Strength Index (RSI). Buys when 'Oversold' (<30) and sells when 'Overbought' (>65).",
    "bollinger_reversion": "Volatility-based strategy using Bollinger Bands. Buys at the Lower Band and sells when the price returns to the 20-day moving average.",
    "macd_momentum": "Momentum strategy using MACD crossovers. Buys when the MACD line crosses above the Signal line, and sells on the reverse crossover.",
    "small_cap_volatility": "High-risk breakout strategy for small caps. Buys on new 20-day highs with strong volume (>1.5x average). Uses tight 5% trailing stops."
}

# Page Configuration
st.set_page_config(
    page_title="Stockholm Quant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS based on ui-ux-pro-max (OLED Dark Mode)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Fira+Sans:wght@300;400;500;600&display=swap');

    :root {
        --primary: #0F172A;
        --secondary: #1E293B;
        --cta: #22C55E;
        --background: #020617;
        --text: #F8FAFC;
        --muted: #475569;
        --border: #1E293B;
    }

    /* Global Styles */
    .main {
        background-color: var(--background);
        font-family: 'Fira Sans', sans-serif;
        color: var(--text);
    }

    h1, h2, h3, .stSubheader {
        font-family: 'Fira Code', monospace !important;
        font-weight: 600 !important;
        color: var(--text) !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: var(--primary) !important;
        border-right: 1px solid var(--border);
    }

    /* Metric Styling */
    [data-testid="stMetric"] {
        background-color: var(--secondary);
        padding: 20px !important;
        border-radius: 12px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        transition: all 0.2s ease-in-out;
    }

    [data-testid="stMetric"]:hover {
        border-color: var(--cta) !important;
        transform: translateY(-2px);
    }

    [data-testid="stMetricValue"] {
        font-family: 'Fira Code', monospace !important;
        font-size: 1.8rem !important;
        color: var(--text) !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        gap: 0;
        padding-top: 10px;
        padding-bottom: 10px;
        color: var(--muted);
        font-family: 'Fira Sans', sans-serif;
    }

    .stTabs [aria-selected="true"] {
        color: var(--cta) !important;
        border-bottom-color: var(--cta) !important;
    }

    /* Dataframe Styling */
    .stDataFrame {
        border: 1px solid var(--border);
        border-radius: 8px;
    }

    /* News Feed */
    .news-item {
        padding: 12px;
        border-bottom: 1px solid var(--border);
        transition: background 0.2s;
    }
    .news-item:hover {
        background-color: rgba(255, 255, 255, 0.03);
    }
    .news-link {
        text-decoration: none !important;
        color: var(--text) !important;
        display: block;
    }
    .news-link:hover {
        color: var(--cta) !important;
    }
    .sentiment-positive { color: #22C55E; font-weight: 600; }
    .sentiment-negative { color: #EF4444; font-weight: 600; }
    .sentiment-neutral { color: #94A3B8; font-weight: 600; }

    /* Button Styling */
    .stButton>button {
        background-color: var(--secondary);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 8px;
        font-family: 'Fira Code', monospace;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: var(--cta);
        color: var(--cta);
    }

    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
def load_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return None

@st.cache_data(ttl=300)
def get_current_prices(tickers):
    """Fetch the latest market prices for a list of tickers."""
    if not tickers:
        return {}
    prices = {}
    try:
        data = yf.download(tickers, period="5d", interval="1m")
        if data is not None and not data.empty:
            for ticker in tickers:
                try:
                    if len(tickers) > 1:
                        price_series = data['Close'][ticker]
                    else:
                        price_series = data['Close']
                    
                    valid_prices = price_series.dropna() if isinstance(price_series, pd.Series) else pd.Series(price_series).dropna()
                    if not valid_prices.empty:
                        prices[ticker] = float(valid_prices.values[-1])
                except Exception:
                    continue
    except Exception as e:
        st.error(f"Error fetching live prices: {e}")
    return prices

@st.cache_data(ttl=900)
def get_live_news(tickers):
    """Fetch live news for the given tickers and return a sorted list."""
    all_news = []
    seen_urls = set()
    
    # Add general market tickers to ensure we always have news
    extended_tickers = list(tickers) + ["VOLV-B.ST", "ERIC-B.ST", "HM-B.ST", "AAPL", "TSLA"]
    
    for ticker_symbol in extended_tickers:
        try:
            t = yf.Ticker(ticker_symbol)
            ticker_news = t.news
            if not ticker_news:
                continue
                
            for item in ticker_news:
                content = item.get('content', item)
                url = content.get('clickThroughUrl', {}).get('url') or content.get('link')
                if not url or url in seen_urls:
                    continue
                
                title = content.get('title')
                if not title:
                    continue
                
                publisher = content.get('provider', {}).get('displayName') or content.get('publisher', 'Finance News')
                ts_raw = content.get('pubDate') or content.get('providerPublishTime')
                ts = 0
                time_str = "Recent"
                
                try:
                    dt_obj = None
                    if isinstance(ts_raw, str):
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

                all_news.append({
                    "time": time_str,
                    "timestamp": ts,
                    "text": title,
                    "url": url,
                    "publisher": publisher
                })
                seen_urls.add(url)
        except Exception:
            continue
            
    all_news.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_news[:25]

config = load_json("config.json")
portfolio_data = load_json("portfolio.json")
equity_history = load_json("data/equity_history.json")

# --- SIDEBAR: ROBOT STATUS & NEWS ---
with st.sidebar:
    st.markdown("## 🤖 Robot Intelligence")
    status_color = "#22C55E" if config and config.get("auto_run") else "#EF4444"
    st.markdown(f"""
        <div style='padding: 10px; border-radius: 8px; border: 1px solid {status_color}; background-color: rgba(0,0,0,0.2); text-align: center;'>
            <span style='color: {status_color}; font-weight: 700;'>{'● ONLINE' if config and config.get("auto_run") else '○ OFFLINE'}</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📰 Live News Feed")
    
    ticker_list_news = config['tickers'] if config else []
    news_feed = get_live_news(ticker_list_news)
    
    if not news_feed:
        st.caption("No recent news found.")
    
    for item in news_feed:
        if item.get('url') and item.get('url') != "None":
            st.markdown(f"""
                <div class="news-item">
                    <a href="{item['url']}" target="_blank" class="news-link">
                        <div style="font-size: 0.75rem; color: var(--muted); display: flex; justify-content: space-between;">
                            <span>{item['publisher']}</span>
                            <span>{item['time']}</span>
                        </div>
                        <div style="font-size: 0.9rem; margin-top: 4px; line-height: 1.3;">{item['text']}</div>
                    </a>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="news-item">
                    <div style="font-size: 0.75rem; color: var(--muted); display: flex; justify-content: space-between;">
                        <span>{item['publisher']}</span>
                        <span>{item['time']}</span>
                    </div>
                    <div style="font-size: 0.9rem; margin-top: 4px; line-height: 1.3; color: var(--text);">{item['text']}</div>
                </div>
            """, unsafe_allow_html=True)

# --- MAIN AREA ---
st.title("Stockholm Quant")

if not portfolio_data:
    st.error("Could not find portfolio.json. Please start the robot first!")
else:
    # Initialize session state for ticker selection
    ticker_list = config['tickers'] if config else ["VOLV-B.ST"]
    
    # Ensure all held positions are in the ticker list for analysis
    all_held = []
    for s_data in portfolio_data.values():
        if isinstance(s_data, dict) and 'positions' in s_data:
            all_held.extend(list(s_data['positions'].keys()))
    
    ticker_list = list(dict.fromkeys(ticker_list + all_held)) # Unique tickers
    
    if 'selected_asset' not in st.session_state:
        st.session_state.selected_asset = ticker_list[0]

    # Dynamically generate tabs
    strategy_ids = [k for k, v in portfolio_data.items() if isinstance(v, dict) and 'positions' in v]
    
    if not strategy_ids:
        st.warning("No active strategies found in portfolio.json.")
        st.stop()

    # --- GLOBAL SELECTION HANDLER ---
    # Check if any position table was clicked to sync the technical analysis view
    for sid in strategy_ids:
        table_key = f"table_{sid}"
        if table_key in st.session_state:
            selection = st.session_state[table_key].get("selection", {}).get("rows", [])
            if selection:
                # Need to reconstruct the list of tickers in that specific table to find the index
                strat_positions = list(portfolio_data[sid]['positions'].keys())
                if selection[0] < len(strat_positions):
                    clicked_ticker = strat_positions[selection[0]]
                    if clicked_ticker != st.session_state.get('selected_asset'):
                        st.session_state.selected_asset = clicked_ticker
                        # Sync all selectboxes BEFORE they are rendered
                        for target_sid in strategy_ids:
                            st.session_state[f"select_{target_sid}"] = clicked_ticker

    tab_names = [f"📊 {s.replace('_', ' ').title()}" for s in strategy_ids] + ["⚔️ Benchmarking"]
    tabs = st.tabs(tab_names)

    plotly_template = "plotly_dark"
    perf_data = {}

    for i, strat_id in enumerate(strategy_ids):
        with tabs[i]:
            strat_name = strat_id.replace('_', ' ').title()
            st.subheader(f"{strat_name} Strategy")
            st.info(STRATEGY_INFO.get(strat_id, "Quantitative trading strategy."))
            
            strat_portfolio = portfolio_data[strat_id]
            active_tickers = list(strat_portfolio['positions'].keys())
            live_prices = get_current_prices(active_tickers)
            
            cost_basis = sum(p['shares'] * p['buy_price'] for p in strat_portfolio['positions'].values())
            market_value = 0
            for t, pos in strat_portfolio['positions'].items():
                price = live_prices.get(t, pos['buy_price'])
                market_value += pos['shares'] * price
                
            total_value = strat_portfolio['cash'] + market_value
            profit_pct = ((total_value / 5000) - 1) * 100
            perf_data[strat_id] = profit_pct

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Value", f"{total_value:,.2f} SEK", f"{profit_pct:+.2f}%")
            m2.metric("Cash Balance", f"{strat_portfolio['cash']:,.2f} SEK")
            m3.metric("Positions", f"{len(strat_portfolio['positions'])} / 5")
            m4.metric("Strategy P&L", f"{total_value - 5000:+.2f} SEK")

            st.divider()
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.markdown("### 📈 Technical Analysis")
                
                selected_index = 0
                if st.session_state.selected_asset in ticker_list:
                    selected_index = ticker_list.index(st.session_state.selected_asset)

                selected_ticker = st.selectbox(
                    f"Select asset to analyze ({strat_id})", ticker_list, index=selected_index, key=f"select_{strat_id}"
                )
                st.session_state.selected_asset = selected_ticker
                
                try:
                    # Download data once for the selected ticker
                    data = yf.download(selected_ticker, period="2y", interval="1d", progress=False)
                    if data is not None and not data.empty:
                        if isinstance(data.columns, pd.MultiIndex):
                            data.columns = data.columns.get_level_values(0)
                    else:
                        data = pd.DataFrame()
                except Exception:
                    data = pd.DataFrame()

                if data is not None and not data.empty:
                    plot_data = data.tail(150).copy() # Last 6 months approx
                    fig = go.Figure()
                    
                    # Base Price Trace
                    fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Close'], name="Price", line=dict(color='#F8FAFC', width=2)))

                    # --- STRATEGY SPECIFIC OVERLAYS ---
                    if strat_id == 'sma_trend':
                        # Use full data for rolling calculation to avoid NaNs at start of slice
                        data_full = data.copy()
                        data_full['SMA50'] = data_full['Close'].rolling(window=50).mean()
                        data_full['SMA200'] = data_full['Close'].rolling(window=200).mean()
                        plot_data['SMA50'] = data_full['SMA50'].tail(150)
                        plot_data['SMA200'] = data_full['SMA200'].tail(150)
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['SMA50'], name="SMA 50", line=dict(color='#22C55E', width=1.5)))
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['SMA200'], name="SMA 200", line=dict(color='#EF4444', width=1.5)))
                    
                    elif strat_id == 'bollinger_reversion':
                        data_full = data.copy()
                        data_full['MA20'] = data_full['Close'].rolling(window=20).mean()
                        data_full['STD20'] = data_full['Close'].rolling(window=20).std()
                        data_full['Upper'] = data_full['MA20'] + (data_full['STD20'] * 2)
                        data_full['Lower'] = data_full['MA20'] - (data_full['STD20'] * 2)
                        plot_data['Upper'] = data_full['Upper'].tail(150)
                        plot_data['Lower'] = data_full['Lower'].tail(150)
                        plot_data['MA20'] = data_full['MA20'].tail(150)
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Upper'], name="Upper Band", line=dict(color='rgba(236, 72, 153, 0.3)', width=1, dash='dot')))
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Lower'], name="Lower Band", line=dict(color='rgba(236, 72, 153, 0.3)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(236, 72, 153, 0.05)'))
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['MA20'], name="MA 20", line=dict(color='#EC4899', width=1)))

                    elif strat_id == 'small_cap_volatility':
                        data_full = data.copy()
                        data_full['High20'] = data_full['High'].rolling(window=20).max().shift(1)
                        plot_data['High20'] = data_full['High20'].tail(150)
                        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['High20'], name="20D High", line=dict(color='#EF4444', width=1, dash='dash')))

                    # Global Layout
                    last_price = float(plot_data['Close'].iloc[-1])
                    fig.add_hline(y=last_price, line_dash="dot", line_color="#94A3B8", annotation_text=f"Last: {last_price:.2f}")
                    fig.update_layout(template=plotly_template, height=400, margin=dict(l=0, r=0, t=20, b=0),
                                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(family="Fira Code", color="#F8FAFC"), xaxis=dict(showgrid=True, gridcolor='#1E293B'),
                                    yaxis=dict(showgrid=True, gridcolor='#1E293B'), hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{strat_id}")

                    # --- STRATEGY SPECIFIC SECONDARY CHARTS ---
                    if strat_id == 'rsi_reversion':
                        # RSI Sub-chart
                        delta = data['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        data['RSI'] = 100 - (100 / (1 + (gain / loss)))
                        rsi_plot = data['RSI'].tail(150)
                        
                        fig_rsi = go.Figure()
                        fig_rsi.add_trace(go.Scatter(x=rsi_plot.index, y=rsi_plot, name="RSI", line=dict(color='#F59E0B', width=2)))
                        fig_rsi.add_hline(y=70, line_color="#EF4444", line_dash="dash")
                        fig_rsi.add_hline(y=30, line_color="#22C55E", line_dash="dash")
                        fig_rsi.update_layout(template=plotly_template, height=200, margin=dict(l=0, r=0, t=10, b=0),
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            yaxis=dict(range=[0, 100], gridcolor='#1E293B'), xaxis=dict(showgrid=True, gridcolor='#1E293B'))
                        st.plotly_chart(fig_rsi, use_container_width=True, key=f"rsi_chart_{strat_id}")

                    elif strat_id == 'macd_momentum':
                        # MACD Sub-chart
                        exp1 = data['Close'].ewm(span=12, adjust=False).mean()
                        exp2 = data['Close'].ewm(span=26, adjust=False).mean()
                        macd = exp1 - exp2
                        signal = macd.ewm(span=9, adjust=False).mean()
                        hist = macd - signal
                        
                        fig_macd = go.Figure()
                        fig_macd.add_trace(go.Scatter(x=plot_data.index, y=macd.tail(150), name="MACD", line=dict(color='#8B5CF6', width=1.5)))
                        fig_macd.add_trace(go.Scatter(x=plot_data.index, y=signal.tail(150), name="Signal", line=dict(color='#F8FAFC', width=1.5, dash='dot')))
                        fig_macd.add_trace(go.Bar(x=plot_data.index, y=hist.tail(150), name="Histogram", marker_color='rgba(139, 92, 246, 0.3)'))
                        fig_macd.update_layout(template=plotly_template, height=200, margin=dict(l=0, r=0, t=10, b=0),
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            yaxis=dict(gridcolor='#1E293B'), xaxis=dict(showgrid=True, gridcolor='#1E293B'))
                        st.plotly_chart(fig_macd, use_container_width=True, key=f"macd_chart_{strat_id}")

                    elif strat_id == 'small_cap_volatility':
                        # Volume Sub-chart
                        fig_vol = go.Figure()
                        fig_vol.add_trace(go.Bar(x=plot_data.index, y=plot_data['Volume'], name="Volume", marker_color='#475569'))
                        fig_vol.update_layout(template=plotly_template, height=150, margin=dict(l=0, r=0, t=10, b=0),
                                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                            yaxis=dict(gridcolor='#1E293B'), xaxis=dict(showgrid=True, gridcolor='#1E293B'))
                        st.plotly_chart(fig_vol, use_container_width=True, key=f"vol_chart_{strat_id}")

                    elif strat_id == 'news_sentiment':
                        # Sentiment Details
                        t_obj = yf.Ticker(selected_ticker)
                        ticker_news = t_obj.news[:10]
                        if ticker_news:
                            sentiments = []
                            for n in ticker_news:
                                title = n.get('content', n).get('title')
                                if title:
                                    s = analyzer.polarity_scores(title)['compound']
                                    sentiments.append({"Title": title[:50]+"...", "Score": s})
                            
                            if sentiments:
                                df_s = pd.DataFrame(sentiments)
                                fig_sent = go.Figure(go.Bar(x=df_s['Score'], y=df_s['Title'], orientation='h', 
                                                           marker_color=['#22C55E' if x > 0 else '#EF4444' if x < 0 else '#94A3B8' for x in df_s['Score']]))
                                fig_sent.update_layout(template=plotly_template, height=300, margin=dict(l=0, r=0, t=10, b=0),
                                                      paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                                      xaxis=dict(title="Sentiment Score", range=[-1, 1], gridcolor='#1E293B'),
                                                      yaxis=dict(showgrid=False))
                                st.plotly_chart(fig_sent, use_container_width=True, key=f"news_chart_{strat_id}")

            with col_right:
                st.markdown("### 📦 Active Positions")
                if strat_portfolio['positions']:
                    pos_list = []
                    for ticker, pos in strat_portfolio['positions'].items():
                        current_p = live_prices.get(ticker, pos['buy_price'])
                        p_change = ((current_p / pos['buy_price']) - 1) * 100
                        pos_list.append({"Ticker": ticker, "Shares": pos['shares'], "Buy": f"{pos['buy_price']:.2f}", "Live": f"{current_p:.2f}", "P&L %": f"{p_change:+.2f}%"})
                    df_pos = pd.DataFrame(pos_list).set_index("Ticker")
                    st.dataframe(df_pos, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"table_{strat_id}")
                    
                    labels = active_tickers + ['Cash']
                    values = [strat_portfolio['positions'][t]['shares'] * live_prices.get(t, strat_portfolio['positions'][t]['buy_price']) for t in active_tickers] + [strat_portfolio['cash']]
                    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, marker=dict(colors=['#3B82F6', '#6366F1', '#8B5CF6', '#EC4899', '#F43F5E', '#1E293B']), textinfo='percent')])
                    fig_pie.update_layout(template=plotly_template, height=300, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(family="Fira Sans", color="#F8FAFC"))
                    st.plotly_chart(fig_pie, use_container_width=True, key=f"pie_{strat_id}")
                else:
                    st.info("No active positions.")

    # Benchmarking Tab (Last)
    with tabs[-1]:
        st.subheader("Strategy Benchmarking")
        
        # 1. Determine Start Date from History
        history_df = pd.DataFrame(equity_history)
        if not history_df.empty:
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
            history_df = history_df.sort_values('timestamp')
            min_date = history_df['timestamp'].min().strftime("%Y-%m-%d")
        else:
            min_date = "2026-03-15"

        st.markdown(f"Comparing active strategies against Swedish indices starting **{min_date}**.")
        
        # 2. Fetch Real Index Data
        @st.cache_data(ttl=3600)
        def get_index_data(start):
            indices = {"OMXS30": "^OMX", "OMXSPI": "^OMXSPI"}
            data = {}
            for name, ticker in indices.items():
                try:
                    df = yf.download(ticker, start=start, progress=False)
                    if df is not None and not df.empty:
                        if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        
                        # Normalize to 5000
                        first_price = float(df['Close'].iloc[0])
                        df['Normalized'] = (df['Close'] / first_price) * 5000
                        data[name] = df
                except Exception:
                    continue
            return data

        index_hist = get_index_data(min_date)
        
        fig_bench = go.Figure()
        
        # 3. Plot Strategies from History
        strategy_colors = {
            'sma_trend': '#22C55E', 
            'news_sentiment': '#3B82F6',
            'rsi_reversion': '#F59E0B',
            'bollinger_reversion': '#EC4899',
            'macd_momentum': '#8B5CF6',
            'small_cap_volatility': '#EF4444'
        }
        
        all_strat_ids = list(history_df['strategy'].unique()) if not history_df.empty else strategy_ids
        for s_id in all_strat_ids:
            s_history = history_df[history_df['strategy'] == s_id]
            if not s_history.empty:
                fig_bench.add_trace(go.Scatter(
                    x=s_history['timestamp'], y=s_history['value'],
                    name=f"{s_id.replace('_', ' ').title()}",
                    line=dict(color=strategy_colors.get(s_id, '#FFFFFF'), width=2.5)
                ))

        # 4. Plot Indices
        index_colors = {"OMXS30": "#94A3B8", "OMXSPI": "#64748B"}
        for name, df in index_hist.items():
            fig_bench.add_trace(go.Scatter(
                x=df.index, y=df['Normalized'],
                name=f"{name} Index",
                line=dict(color=index_colors.get(name), width=2, dash='dot')
            ))
            
        fig_bench.update_layout(
            template=plotly_template, height=600,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#1E293B', title="Date"),
            yaxis=dict(gridcolor='#1E293B', title="Value (SEK)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bench, use_container_width=True)
        
        # 5. Performance Table
        st.markdown("### 📊 Absolute Performance")
        rows = []
        for s_id in all_strat_ids:
            s_history = history_df[history_df['strategy'] == s_id]
            if not s_history.empty:
                val_start = s_history.iloc[0]['value']
                val_end = s_history.iloc[-1]['value']
                ret = ((val_end / val_start) - 1) * 100
                rows.append({"Source": s_id.replace('_', ' ').title(), "Return": f"{ret:+.2f}%", "Status": "Live"})
        
        for name, df in index_hist.items():
            ret = ((float(df['Close'].iloc[-1]) / float(df['Close'].iloc[0])) - 1) * 100
            rows.append({"Source": f"{name} Index", "Return": f"{ret:+.2f}%", "Status": "Benchmark"})
        
        st.table(pd.DataFrame(rows))

# Manual Refresh Button
if st.button("🔄 Refresh Dashboard"):
    st.rerun()
