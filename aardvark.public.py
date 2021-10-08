#!/usr/bin/python3
import base64
import datetime, time
import hashlib
import hmac
import json
import random
import requests
import ssl
import websocket

class order:
    """Place a buy or sell limit order

    https://docs.gemini.com/rest-api/#private-api-invocation
    """

    def place_order(self, symbol, amount, price, side):
        payload_nonce = self.make_nonce()
        client_order_id = "aardvark-{}".format(payload_nonce)

        payload = {
            "request": "/v1/order/new",
            "nonce": payload_nonce,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "side": side,
            "type": "exchange limit"
        }

        url = "https://api.sandbox.gemini.com/v1/order/new"
        request_headers = self.build_request(payload)
        response = requests.post(url, headers=request_headers)
        
        self.order_id = response.json()['order_id']
        self.symbol = symbol
        self.amount = amount
        self.p_filled = price
        self.last_side = side

        return response.json()
    
    def make_nonce(self):
        t = datetime.datetime.now()
        nonce = str( int(round( time.time() * 1000 ) ) )
        return nonce

    def build_request(self, payload):
        gemini_api_key = "account-your_api_key"
        gemini_api_secret = "your-api-secret".encode()

        encoded_payload = json.dumps(payload).encode()
        b64 = base64.b64encode(encoded_payload)
        signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()

        request_headers = {
            'Content-Type': "text/plain",
            'Content-Length': "0",
            'X-GEMINI-APIKEY': gemini_api_key,
            'X-GEMINI-PAYLOAD': b64,
            'X-GEMINI-SIGNATURE': signature,
            'Cache-Control': "no-cache"
        }

        return request_headers

    def get_status(self, order_id):
        payload_nonce = self.make_nonce()
        payload = {
            "request": "/v1/order/status",
            "nonce": payload_nonce,
            "order_id": order_id,
        }

        url = "https://api.sandbox.gemini.com/v1/order/status"
        request_headers = self.build_request(payload)
        response = requests.post(url, headers=request_headers)

        return response.json()

    def get_price(self, symbol):
        base_url = "https://api.sandbox.gemini.com/v1"
        response = requests.get( "{}/pubticker/{}".format(base_url, symbol) )
        data = response.json()

        return data['last']

    def get_balance(self, currency):
        currency = currency.upper()
        payload_nonce = self.make_nonce()

        payload = {
            "request": "/v1/balances",
            "nonce": payload_nonce,
        }

        url = "https://api.sandbox.gemini.com/v1/balances"
        request_headers = self.build_request(payload)
        response = requests.post(url, headers=request_headers)

        # Pull available balance from response
        available_balance = 0
        balances = response.json()
        for balance in balances:
            if balance['currency'] == currency:
                available_balance = balance['availableForWithdrawal']
                break
                
        return available_balance
    
    def get_delta(self, symbol):
        # Ideally get_delta() is called when get_status() throws an order complete event
        if symbol != self.symbol:
            return

        start_price = self.get_price(symbol)

        # check that p_n_minus_1, p_filled and last_side exist
        if symbol != self.symbol:
            return

        if hasattr(self, 'p_n') == False:
            self.p_n_minus_1 = start_price
        else:
            self.p_n_minus_1 = self.p_n

        if hasattr(self, 'p_filled') == False:
            self.p_filled = start_price
        
        if self.last_side == "sell":
            self.side = "buy"
        else:
            self.side = "sell"

        # Get current price
        self.p_n = self.get_price(symbol)
        
        delta = float(self.p_n) - float(self.p_n_minus_1)
                
        return delta

    def run_aardvark(self):
        # API request limits:
        # Public API: 120 requets per minute
        # Private API: 600 requests per minute
        #
        # https://gemini.com/api-agreement/#request-limits

        print("Run Aardvark")

        # Get available balance
        balance_usd = float( self.get_balance("USD") )
        print( "balance USD = {}".format(balance_usd) )
        balance_symbol = self.get_balance( self.symbol[:3] )
        print( "balance {} = {}".format( self.symbol[:3], balance_symbol ) )
        
        # Listen for completed order
        delta = 0
        side = "hold"
        while True:
            time.sleep(0.5)
            min_delta = False
            side = "hold"

            delta = self.get_delta(self.symbol)
            if delta > 0:
                side = "buy"
            if delta < 0:
                side = "sell"
            if abs(delta) > ( 0.0035 * float(self.p_n) ):
                min_delta = True
                print( "delta = {}\tmin_delta = {}\tside = {}\tself.side = {}".format(delta, min_delta, side, self.side) )
            
            # Make a trade
            p_n = float(self.p_n)
            p_filled = float(self.p_filled)
            if ( min_delta and (self.side == side) ):
                print( "p_n = {}\tp_filled = {}".format(p_n, p_filled) )
                if ( (side == "sell") and ( p_n >= p_filled ) ):
                    # Sell
                    # Limit price should be 100.35% (100% + 0.35%) of last trade price
                    # but in practice the taker penalty applies below 100.65%
                    print("sell")
                    limit_price = p_n * 1.0065
                    amount = float(balance_symbol)
                elif ( (side == "buy") and ( p_n < p_filled ) ):
                    # Buy
                    # Limit price should be 99.65% (100% - 0.35%) of last trade price
                    # but in practice the taker penalty applies above 99.35%
                    print("buy")
                    limit_price = p_n * 0.9935
                    amount = ( balance_usd * 0.99 ) / p_n
                else:
                    # Hold
                    continue

                # Format decimals
                symbol = self.symbol.lower()
                str_limit_price = "{0:0.2f}".format(limit_price)
                if (symbol == "btcusd") or (symbol == "bchusd"):
                    str_amount = "{0:0.8f}".format(amount)
                else:
                    str_amount = "{0:0.6f}".format(amount)


                print("Begin place order\tstr_amount = {}\tstr_limit_price = {}".format(str_amount, str_limit_price))
                status = self.place_order(self.symbol, str_amount, str_limit_price, self.side)
                print( "Place order:\n{}".format(status) )
                break
                                
        return True

class order_listener:
    def __init__(self, symbol):
        self.gemini_api_key = "account-your_api_key"
        gemini_api_secret = "your-api-secret".encode()

        payload = {
            "request": "/v1/order/events",
            "nonce": int( time.time()*1000 )
        }
        encoded_payload = json.dumps(payload).encode()
        self.b64 = base64.b64encode(encoded_payload)
        self.signature = hmac.new(gemini_api_secret, self.b64, hashlib.sha384).hexdigest()

        self.open_socket(symbol)

    def open_socket(self, symbol):
        endpoint = "wss://api.sandbox.gemini.com/v1/order/events"
        symbol_filter = "symbolFilter={}".format(symbol)
        event_filters = "eventTypeFilter=fill&eventTypeFilter=closed"
        ws = websocket.WebSocketApp(
            "{}?{}&{}".format(endpoint, symbol_filter, event_filters),
            on_message = self.on_message,
            header={
                'X-GEMINI-PAYLOAD': self.b64.decode(),
                'X-GEMINI-APIKEY': self.gemini_api_key,
                'X-GEMINI-SIGNATURE': self.signature
            })
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def on_message(ws, message):
        print( "\n{}\n".format(message) )
        m_json = json.loads(message)

        if type(m_json) is dict:
            return # just a heartbeat message

        # Check if message has order that is is closed, finished and valid
        for m_order in m_json:
            is_closed = False
            is_finished = False
            is_valid = False
            if m_order['type'] == "closed":
                is_closed = True
            if m_order['is_live'] == False:
                is_finished = True
            if  m_order['is_cancelled'] == False:
                is_valid = True
            if is_closed and is_finished and is_valid:
                # When receive order complete event then run Aardvark
                symbol = m_order['symbol']
                side = m_order['side']
                p_filled = m_order['avg_execution_price']
                order_listener.run_aardvark(symbol, side, p_filled)
                return

    def run_aardvark(symbol, last_side, p_filled):
        new_order = order()
        new_order.symbol = symbol
        new_order.last_side = last_side
        new_order.p_filled = p_filled

        new_order.run_aardvark()

    def on_error(ws, error):
        print(error)

    def on_close(ws):
        print("### closed ###")        
            
def main():
    # Instructions
    print("INSTRUCTIONS:\n\ntmux-session:$ python3 -u aardvark.py | tee aardvark.out\n")

    # Test variables
    test_symbol = "btcusd"
    print( "\n****** symbol = {} ******\n".format(test_symbol) )

    # Listen for trade complete
    listener = order_listener(test_symbol)

if __name__ == "__main__":
    main()
