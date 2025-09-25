import requests

ALPHA_VANTAGE_KEY = "G8QRFBF7WH0ABNQ2"

def get_stock_price(symbol):
    """
    Fetch latest stock price from Alpha Vantage
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}"
    try:
        resp = requests.get(url).json()
        quote = resp.get("Global Quote", {})
        price = quote.get("05. price")
        change = quote.get("10. change percent")
        if price and change:
            return f"{symbol} price: ${price}, Change: {change}"
        else:
            return f"Could not fetch data for {symbol}."
    except:
        return f"Error fetching stock data for {symbol}."
