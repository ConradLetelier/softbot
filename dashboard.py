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
                ticker_news = []
                avg_sentiment = 0.0
                if strat_id == 'news_sentiment':
                    try:
                        t_obj = yf.Ticker(st.session_state.selected_asset)
                        ticker_news = t_obj.news
                        if ticker_news:
                            scores = []
                            for item in ticker_news:
                                content = item.get('content', item)
                                title = content.get('title')
                                if title:
                                    scores.append(analyzer.polarity_scores(title)['compound'])
                            if scores:
                                avg_sentiment = sum(scores) / len(scores)
                    except Exception:
                        pass
                
                selected_index = 0
                if st.session_state.selected_asset in ticker_list:
                    selected_index = ticker_list.index(st.session_state.selected_asset)

                selected_ticker = st.selectbox(
                    f"Select asset to analyze ({strat_id})", ticker_list, index=selected_index, key=f"select_{strat_id}"
                )
                st.session_state.selected_asset = selected_ticker
                
                if strat_id == 'news_sentiment':
                    s_color = "#22C55E" if avg_sentiment >= 0.35 else "#EF4444" if avg_sentiment <= -0.1 else "#94A3B8"
                    st.markdown(f"""
                        <div style="background-color: var(--secondary); padding: 15px; border-radius: 10px; border-left: 5px solid {s_color}; margin-bottom: 20px;">
                            <div style="font-size: 0.8rem; color: var(--muted); text-transform: uppercase;">Average News Sentiment</div>
                            <div style="font-size: 1.8rem; font-weight: 700; color: {s_color};">{avg_sentiment:+.2f}</div>
                            <div style="font-size: 0.75rem; color: var(--muted);">Based on {len(ticker_news)} recent articles</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                try:
                    data = yf.download(selected_ticker, period="2y", interval="1d")
                    if data is not None and not data.empty:
                        if isinstance(data.columns, pd.MultiIndex):
                            data.columns = data.columns.get_level_values(0)
                except Exception:
                    data = pd.DataFrame()

                if data is not None and not data.empty:
                    data['SMA50'] = data['Close'].rolling(window=50).mean()
                    data['SMA200'] = data['Close'].rolling(window=200).mean()
                    plot_data = data.tail(252)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Close'], name="Price", line=dict(color='#F8FAFC', width=2)))
                    fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['SMA50'], name="SMA 50", line=dict(color='#22C55E', width=2)))
                    fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data['SMA200'], name="SMA 200", line=dict(color='#EF4444', width=2)))
                    last_price = float(plot_data['Close'].iloc[-1])
                    fig.add_hline(y=last_price, line_dash="dot", line_color="#94A3B8", annotation_text=f"Last: {last_price:.2f}", annotation_position="bottom right")
                    fig.update_layout(template=plotly_template, height=450, margin=dict(l=0, r=0, t=20, b=0),
                                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(family="Fira Code", color="#F8FAFC"), xaxis=dict(showgrid=True, gridcolor='#1E293B'),
                                    yaxis=dict(showgrid=True, gridcolor='#1E293B'), hovermode="x unified")
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{strat_id}")

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
        st.markdown("Comparing active strategies against Swedish indices starting **March 15, 2026**.")
        
        start_date = "2026-03-15"
        
        # 1. Fetch Real Index Data
        @st.cache_data(ttl=3600)
        def get_index_data(start):
            indices = {"OMXS30": "^OMX", "OMXSPI": "^OMXSPI"}
            data = {}
            for name, ticker in indices.items():
                try:
                    df = yf.download(ticker, start=start, progress=False)
                    if df is not None and not df.empty:
                        # Handle MultiIndex if present
                        if hasattr(df, 'columns') and isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        
                        # Normalize to 5000
                        first_price = float(df['Close'].iloc[0])
                        df['Normalized'] = (df['Close'] / first_price) * 5000
                        data[name] = df
                except Exception:
                    continue
            return data

        index_hist = get_index_data(start_date)
        
        # 2. Process Equity History
        history_df = pd.DataFrame(equity_history)
        if not history_df.empty:
            history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
            history_df = history_df.sort_values('timestamp')
            
        fig_bench = go.Figure()
        
        # Plot Strategies from History
        colors = {'sma_trend': '#22C55E', 'news_sentiment': '#3B82F6'}
        for s_id in strategy_ids:
            s_history = history_df[history_df['strategy'] == s_id]
            if not s_history.empty:
                fig_bench.add_trace(go.Scatter(
                    x=s_history['timestamp'], y=s_history['value'],
                    name=f"{s_id.replace('_', ' ').title()} (Actual)",
                    line=dict(color=colors.get(s_id, '#FFFFFF'), width=3)
                ))

        # Plot Indices
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
        
        # Performance Table
        st.markdown("### 📊 Absolute Performance")
        rows = []
        for s_id in strategy_ids:
            rows.append({"Source": s_id.replace('_', ' ').title(), "Return": f"{perf_data.get(s_id, 0):+.2f}%", "Status": "Live"})
        for name, df in index_hist.items():
            ret = ((float(df['Close'].iloc[-1]) / float(df['Close'].iloc[0])) - 1) * 100
            rows.append({"Source": f"{name} Index", "Return": f"{ret:+.2f}%", "Status": "Benchmark"})
        
        st.table(pd.DataFrame(rows))

# Manual Refresh Button
if st.button("🔄 Refresh Dashboard"):
    st.rerun()
