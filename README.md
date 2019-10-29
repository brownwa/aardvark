# aardvark
High frequency trading program for cryptocurrencies on the Gemini.com digital asset exchange

# Summary
Aardvark uses [Gemini APIs](https://docs.gemini.com/rest-api/) to arbitrage a single cryptocurrency against the US dollar (USD). The algorithm simply buys low and sells high, using local maxima and minima as triggers.

# Design Choices
## Observer Pattern (pub/sub)
## Price Polling

# order Class
## Instance Methods
### order.place_order(symbol, amount, price, side)
- Parameter: symbol; the six character string of a cryptocurrency relative to the USD, eg; btcusd (Bitcoin)
- Parameter: amount; the string of the amount of cryptocurrency to trade, eight decimal digits for btcusd and bchusd, six otherwise
- Parameter: price; string representation of the desired limit price of the symbol
- Parameter: side; whether you want to place a "buy" or "sell" order
- Returns: JSON encoded string of the Gemini API response from placing an order
Make an API call for a buy or sell order (limit orders only)
### order.make_nonce()
- Parameter:
- Returns:
Supporting method for place_order()
### order.build_request()
- Parameter:
- Returns:
Supporting method for place_order()
### order.get_status(order_id)
- Parameter:
- Returns:
Legacy method whose function was replaced by the order_listner class. I left it in the code because it's handy
### order.get_price(symbol)
- Parameter: symbol; the six character string of a cryptocurrency relative to the USD, eg; btcusd (Bitcoin)
- Returns: price; String representation of the price
Direct API call to get the last closing price of a cryptocurrency symbol (against the USD, eg; btcusd)
### order.get_balance(currency)
- Parameter:
- Returns:
Get the balance of a desired currency (crypto or USD) in your account
### order.get_delta(symbol)
- Parameter:
- Returns:
The key to the aardvark algorithm. get_delta() provides both the magnitude of a price change and the direction. For example, a negative delta means the price dropped from the last 0.5 second polling interval
# order_listener Class

# Limitations
## Starting Aardvark
## Trading Volume
## Order Filling
## Request Limits
https://gemini.com/api-agreement/#request-limits

# Risks
## Currency Stability Risk
## Gemini Platform Risk
## Exchange Rate Risk
## Standard Deviation Risk

# Suggested Enhancements
