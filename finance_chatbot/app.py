import streamlit as st
import os
import requests
import re
import time
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from typing import Dict, List, Tuple, Optional

# -------------------------------
# PAGE CONFIGURATION
# -------------------------------
st.set_page_config(
    page_title="Global Finance AI Assistant", 
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------
# CONFIGURE API KEYS
# -------------------------------
try:
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
    ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
    NEWS_API_KEY = st.secrets.get("NEWS_API_KEY", "")
    
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
    else:
        st.warning("⚠️ Google API key not configured. AI responses will use fallback mode.")
        
    if not ALPHA_VANTAGE_KEY:
        st.warning("⚠️ Alpha Vantage API key not configured. Market data may be limited.")
        
    if not NEWS_API_KEY:
        st.warning("⚠️ News API key not configured. News features will be limited.")
        
except Exception as e:
    st.error(f"Configuration error: {str(e)}")

# -------------------------------
# ENHANCED SYMBOLS DATABASE
# -------------------------------

# Major Global Stock Exchanges
STOCK_EXCHANGES = {
    "US": {"NSE": "National Stock Exchange", "BSE": "Bombay Stock Exchange"},
    "India": {"NSE": ".NS", "BSE": ".BO"},
    "UK": {"LSE": ".L"},
    "Japan": {"TSE": ".T"},
    "Germany": {"XETRA": ".DE"},
    "Canada": {"TSX": ".TO"},
    "Australia": {"ASX": ".AX"}
}

# Popular Indian Stocks
INDIAN_STOCKS = {
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
    "hdfc bank": "HDFCBANK.NS", "icici bank": "ICICIBANK.NS", "sbi": "SBIN.NS",
    "bharti airtel": "BHARTIARTL.NS", "itc": "ITC.NS", "wipro": "WIPRO.NS",
    "maruti": "MARUTI.NS", "bajaj finance": "BAJFINANCE.NS", "asian paints": "ASIANPAINT.NS",
    "tata motors": "TATAMOTORS.NS", "titan": "TITAN.NS", "adani enterprises": "ADANIENT.NS",
    "nifty": "^NSEI", "sensex": "^BSESN", "bank nifty": "^NSEBANK"
}

# Popular US Stocks
US_STOCKS = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL", "amazon": "AMZN",
    "tesla": "TSLA", "meta": "META", "nvidia": "NVDA", "netflix": "NFLX",
    "facebook": "META", "alphabet": "GOOGL", "berkshire": "BRK-B",
    "johnson": "JNJ", "walmart": "WMT", "visa": "V", "mastercard": "MA",
    "sp500": "^GSPC", "nasdaq": "^IXIC", "dow": "^DJI"
}

# Commodities
COMMODITIES = {
    "gold": "GC=F", "silver": "SI=F", "crude oil": "CL=F", "brent oil": "BZ=F",
    "natural gas": "NG=F", "copper": "HG=F", "platinum": "PL=F", "palladium": "PA=F",
    "corn": "C=F", "wheat": "W=F", "soybeans": "S=F", "coffee": "KC=F",
    "sugar": "SB=F", "cotton": "CT=F"
}

# Forex Pairs
FOREX_PAIRS = {
    "eurusd": "EURUSD=X", "gbpusd": "GBPUSD=X", "usdjpy": "USDJPY=X",
    "usdchf": "USDCHF=X", "audusd": "AUDUSD=X", "usdcad": "USDCAD=X",
    "nzdusd": "NZDUSD=X", "usdinr": "USDINR=X", "eurjpy": "EURJPY=X",
    "gbpjpy": "GBPJPY=X", "chfjpy": "CHFJPY=X", "eurgbp": "EURGBP=X"
}

# Cryptocurrencies
CRYPTO_PAIRS = {
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "cardano": "ADA-USD",
    "solana": "SOL-USD", "dogecoin": "DOGE-USD", "litecoin": "LTC-USD",
    "chainlink": "LINK-USD", "polygon": "MATIC-USD", "avalanche": "AVAX-USD"
}

# -------------------------------
# UTILITY FUNCTIONS
# -------------------------------

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_yahoo_finance_data(symbol: str) -> Dict:
    """Fetch real-time data from Yahoo Finance API alternative"""
    try:
        # Using Alpha Vantage for real-time data
        url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        quote = data.get("Global Quote", {})
        if quote:
            return {
                "symbol": quote.get("01. symbol", symbol),
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                "volume": quote.get("06. volume", "N/A"),
                "timestamp": datetime.now()
            }
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
    return None

@st.cache_data(ttl=300)
def get_forex_data(pair: str) -> Dict:
    """Fetch forex data from Alpha Vantage"""
    try:
        from_curr = pair[:3]
        to_curr = pair[3:6] if len(pair) > 3 else pair[3:]
        
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={from_curr}&to_currency={to_curr}&apikey={ALPHA_VANTAGE_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        rate_data = data.get("Realtime Currency Exchange Rate", {})
        if rate_data:
            return {
                "pair": f"{from_curr}/{to_curr}",
                "rate": float(rate_data.get("5. Exchange Rate", 0)),
                "timestamp": rate_data.get("6. Last Refreshed", "")
            }
    except Exception as e:
        st.error(f"Error fetching forex data: {str(e)}")
    return None

@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_financial_news(category: str = "business", country: str = "us", top_n: int = 5) -> List[Dict]:
    """Fetch latest financial news"""
    try:
        url = f"https://newsapi.org/v2/top-headlines?category={category}&country={country}&pageSize={top_n}&apiKey={NEWS_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        articles = []
        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "source": article.get("source", {}).get("name", ""),
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", "")
            })
        return articles
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
    return []

def find_symbol(query: str) -> Optional[str]:
    """Find symbol from user query using fuzzy matching"""
    query = query.lower().strip()
    
    # Check all symbol dictionaries
    all_symbols = {**INDIAN_STOCKS, **US_STOCKS, **COMMODITIES, **FOREX_PAIRS, **CRYPTO_PAIRS}
    
    # Direct match
    if query in all_symbols:
        return all_symbols[query]
    
    # Partial match
    for name, symbol in all_symbols.items():
        if query in name or name in query:
            return symbol
    
    # Symbol search via Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={ALPHA_VANTAGE_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        matches = data.get("bestMatches", [])
        if matches:
            return matches[0].get("1. symbol")
    except:
        pass
    
    return None

def generate_ai_response(user_query: str, context_data: str = "") -> str:
    """Generate AI response using Gemini with fallback options"""
    try:
        # Try different model names that might be available
        model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'models/gemini-pro']
        
        model = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except:
                continue
        
        if not model:
            return generate_fallback_response(user_query, context_data)
        
        prompt = f"""
        You are a highly knowledgeable financial advisor and market analyst with expertise in:
        - Global stock markets (US, India, Europe, Asia)  
        - Forex trading and currency analysis
        - Commodity markets and precious metals
        - Cryptocurrency markets
        - Economic indicators and market trends
        - Personal finance and investment strategies
        - Risk management and portfolio optimization
        
        Current market context:
        {context_data}
        
        User question: {user_query}
        
        Provide a comprehensive, accurate, and actionable response. Include:
        - Relevant market data and analysis
        - Investment insights and recommendations
        - Risk factors to consider
        - Current market trends
        
        Keep the response conversational yet professional, around 150-200 words.
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return generate_fallback_response(user_query, context_data)

def generate_fallback_response(user_query: str, context_data: str = "") -> str:
    """Generate fallback response when AI is not available"""
    query_lower = user_query.lower()
    
    # Stock price queries
    if any(word in query_lower for word in ['price', 'stock', 'share']):
        symbol = find_symbol(user_query)
        if symbol:
            data = get_yahoo_finance_data(symbol)
            if data:
                change_indicator = "📈" if float(data["change"]) >= 0 else "📉"
                return f"""
                {change_indicator} **{data['symbol']} Current Price**: ${data['price']:.2f}
                **Change**: {data['change']:+.2f} ({data['change_percent']}%)
                **Volume**: {data['volume']}
                **Last Updated**: {data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                
                {context_data}
                
                💡 **Quick Analysis**: The stock is currently {'gaining' if float(data['change']) >= 0 else 'declining'}. 
                Consider checking recent news and market trends before making investment decisions.
                """
    
    # Market overview queries
    elif any(word in query_lower for word in ['market', 'global', 'overview', 'trend']):
        return """
        🌍 **Global Market Overview**
        
        The global financial markets are interconnected and influenced by various factors:
        
        📊 **Key Market Drivers**:
        - Economic indicators (GDP, inflation, employment)
        - Central bank policies and interest rates
        - Geopolitical events and trade relations
        - Corporate earnings and sector performance
        
        🔍 **Current Focus Areas**:
        - US Federal Reserve policy decisions
        - China's economic recovery
        - European energy markets
        - Emerging market currencies
        
        💡 **Investment Tip**: Diversification across regions and asset classes helps manage risk in volatile markets.
        """
    
    # Forex queries
    elif any(word in query_lower for word in ['forex', 'currency', 'exchange', 'usd', 'eur', 'inr']):
        return """
        💱 **Forex Market Insights**
        
        Currency markets are the most liquid financial markets globally, trading $7.5 trillion daily.
        
        **Major Currency Pairs**:
        - EUR/USD: Most traded pair, affected by ECB and Fed policies
        - USD/JPY: Safe-haven flows influence this pair
        - GBP/USD: Brexit and UK economic data drive movements
        - USD/INR: Influenced by India's trade balance and RBI policies
        
        **Key Factors Affecting Forex**:
        - Interest rate differentials
        - Economic growth rates
        - Political stability
        - Trade balances
        
        ⚠️ **Risk Warning**: Forex trading involves high leverage and significant risk.
        """
    
    # Commodity queries
    elif any(word in query_lower for word in ['gold', 'oil', 'commodity', 'silver', 'crude']):
        return """
        🏆 **Commodity Market Analysis**
        
        Commodities serve as inflation hedges and portfolio diversifiers.
        
        **Precious Metals**:
        - Gold: Traditional safe-haven asset, influenced by USD strength and inflation
        - Silver: Industrial and investment demand drives prices
        
        **Energy**:
        - Crude Oil: Affected by supply disruptions, demand growth, and OPEC decisions
        - Natural Gas: Seasonal demand and supply infrastructure impact prices
        
        **Agricultural**:
        - Weather patterns, crop yields, and global food demand influence prices
        
        💡 **Investment Note**: Commodities can be volatile but provide portfolio diversification benefits.
        """
    
    # Investment advice queries
    elif any(word in query_lower for word in ['invest', 'portfolio', 'strategy', 'advice']):
        return """
        💰 **Investment Strategy Guidance**
        
        **Key Investment Principles**:
        1. **Diversification**: Spread risk across asset classes and regions
        2. **Time Horizon**: Align investments with your financial goals
        3. **Risk Tolerance**: Only invest what you can afford to lose
        4. **Regular Review**: Monitor and rebalance your portfolio
        
        **Asset Allocation Guidelines**:
        - **Conservative**: 60% bonds, 40% stocks
        - **Moderate**: 50% stocks, 40% bonds, 10% alternatives
        - **Aggressive**: 80% stocks, 15% bonds, 5% alternatives
        
        **Before Investing**:
        - Build an emergency fund (3-6 months expenses)
        - Pay off high-interest debt
        - Define clear financial goals
        
        ⚠️ **Disclaimer**: This is educational content, not personalized financial advice.
        """
    
    else:
        return """
        🤖 **Finance AI Assistant**
        
        I'm here to help with your financial questions! I can provide information about:
        
        📈 **Markets**: Stock prices, market analysis, and trends
        💱 **Forex**: Currency exchange rates and trading insights  
        🏆 **Commodities**: Gold, oil, and other commodity prices
        💰 **Investment**: Portfolio strategies and risk management
        📊 **Analysis**: Technical and fundamental market analysis
        
        **Try asking**:
        - "What's Apple's stock price?"
        - "USD to INR exchange rate"
        - "Gold price analysis"
        - "Best investment strategies for beginners"
        
        How can I assist you with your financial needs today?
        """

# -------------------------------
# MAIN STREAMLIT APP
# -------------------------------

def main():
    # Custom CSS for better UI
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79, #2e8b57);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f4e79;
        margin: 0.5rem 0;
    }
    .chat-container {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: #fafafa;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🌍 Global Finance AI Assistant</h1>
        <p>Your intelligent companion for stocks, forex, commodities & financial insights worldwide</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for quick market overview
    with st.sidebar:
        st.header("📊 Quick Market Overview")
        
        # Major Indices
        st.subheader("Major Indices")
        indices = ["^NSEI", "^BSESN", "^GSPC", "^IXIC"]
        for idx in indices:
            data = get_yahoo_finance_data(idx)
            if data:
                change_color = "green" if float(data["change"]) >= 0 else "red"
                st.markdown(f"""
                <div class="metric-container">
                    <strong>{data['symbol']}</strong><br>
                    <span style="font-size: 1.2em">{data['price']:.2f}</span>
                    <span style="color: {change_color}">({data['change']:+.2f})</span>
                </div>
                """, unsafe_allow_html=True)
        
        # Currency Rates
        st.subheader("Currency Rates")
        forex_pairs = ["USDINR", "EURUSD", "GBPUSD"]
        for pair in forex_pairs:
            forex_data = get_forex_data(pair)
            if forex_data:
                st.metric(
                    label=forex_data["pair"],
                    value=f"{forex_data['rate']:.4f}"
                )
        
        # Commodities
        st.subheader("Commodities")
        commodities = ["GC=F", "CL=F"]  # Gold, Crude Oil
        for comm in commodities:
            data = get_yahoo_finance_data(comm)
            if data:
                st.metric(
                    label=data["symbol"],
                    value=f"${data['price']:.2f}",
                    delta=f"{data['change']:+.2f}"
                )
    
    # Main chat interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Chat with Finance AI")
        
        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about stocks, forex, commodities, or any financial question..."):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Analyzing markets and generating response..."):
                    
                    context_data = ""
                    
                    # Check if user is asking for specific market data
                    if any(keyword in prompt.lower() for keyword in ["price", "stock", "rate", "forex", "commodity"]):
                        symbol = find_symbol(prompt)
                        if symbol:
                            if "=" in symbol or symbol.endswith("=X"):
                                # Forex or commodity
                                market_data = get_yahoo_finance_data(symbol)
                            else:
                                # Stock
                                market_data = get_yahoo_finance_data(symbol)
                            
                            if market_data:
                                context_data = f"Current data for {symbol}: Price: {market_data['price']}, Change: {market_data['change']} ({market_data['change_percent']}%)"
                    
                    # Get recent news for context
                    news = get_financial_news(top_n=3)
                    if news:
                        news_context = "Recent financial news: " + "; ".join([article["title"] for article in news[:3]])
                        context_data += f"\n{news_context}"
                    
                    # Generate AI response
                    response = generate_ai_response(prompt, context_data)
                    
                    st.markdown(response)
            
            # Add assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    with col2:
        st.header("📈 Market Tools")
        
        # Quick quote lookup
        st.subheader("Quick Quote")
        symbol_input = st.text_input("Enter symbol or company name:")
        if symbol_input:
            symbol = find_symbol(symbol_input)
            if symbol:
                data = get_yahoo_finance_data(symbol)
                if data:
                    st.success(f"**{data['symbol']}**")
                    st.metric(
                        label="Current Price",
                        value=f"${data['price']:.2f}",
                        delta=f"{data['change']:+.2f} ({data['change_percent']}%)"
                    )
        
        # News section
        st.subheader("📰 Latest Financial News")
        news = get_financial_news(top_n=5)
        for article in news:
            with st.expander(f"{article['source']} - {article['title'][:50]}..."):
                st.write(article['description'])
                st.markdown(f"[Read more]({article['url']})")
        
        # Market categories
        st.subheader("🎯 Popular Categories")
        categories = {
            "🇮🇳 Indian Stocks": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
            "🇺🇸 US Tech": ["AAPL", "MSFT", "GOOGL"],
            "💰 Commodities": ["GC=F", "CL=F", "SI=F"],
            "💱 Forex": ["USDINR=X", "EURUSD=X", "GBPUSD=X"]
        }
        
        for category, symbols in categories.items():
            with st.expander(category):
                for symbol in symbols:
                    data = get_yahoo_finance_data(symbol)
                    if data:
                        change_color = "🟢" if float(data["change"]) >= 0 else "🔴"
                        st.write(f"{change_color} **{data['symbol']}**: ${data['price']:.2f}")

if __name__ == "__main__":
    main()