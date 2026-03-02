# Fix SSL CERTIFICATE_VERIFY_FAILED on server/Windows (unable to get local issuer certificate)
# Apply before any Fyers/websocket imports so the library uses unverified context when connecting.
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass
try:
    def _unverified_default_context(purpose=ssl.Purpose.SERVER_AUTH):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    ssl.create_default_context = _unverified_default_context
except Exception:
    pass
# Fyers uses websocket-client for the data socket; patch both create_connection and WebSocketApp to disable cert verification
try:
    import websocket
    _orig_create_connection = websocket.create_connection
    def _create_connection_no_verify(*args, **kwargs):
        kwargs.setdefault("sslopt", {})
        if isinstance(kwargs["sslopt"], dict):
            kwargs["sslopt"]["cert_reqs"] = ssl.CERT_NONE
            kwargs["sslopt"].setdefault("check_hostname", False)
        return _orig_create_connection(*args, **kwargs)
    websocket.create_connection = _create_connection_no_verify

    # WebSocketApp.run_forever also needs sslopt when it opens the connection
    _orig_WebSocketApp = websocket.WebSocketApp
    class _WebSocketAppNoVerify(_orig_WebSocketApp):
        def run_forever(self, **kwargs):
            kwargs.setdefault("sslopt", {})
            if isinstance(kwargs["sslopt"], dict):
                kwargs["sslopt"]["cert_reqs"] = ssl.CERT_NONE
                kwargs["sslopt"].setdefault("check_hostname", False)
            return _orig_WebSocketApp.run_forever(self, **kwargs)
    websocket.WebSocketApp = _WebSocketAppNoVerify
except Exception:
    pass

from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws
import webbrowser
from datetime import datetime, timedelta, date
from time import sleep
import os
import pyotp
import requests
import json
import math
import pytz
from urllib.parse import parse_qs, urlparse
import warnings
import pandas as pd
access_token=None
fyers=None
shared_data = {}
shared_data_2 = {}
# Lock to ensure thread-safe access to the shared data
def apiactivation(client_id,redirect_uri,response_type,state,secret_key,grant_type):
    appSession = fyersModel.SessionModel(client_id = client_id, redirect_uri = redirect_uri,
                                         response_type=response_type,state=state,
                                         secret_key=secret_key,grant_type=grant_type)# ## Make  a request to generate_authcode object this will return a login url which you need to open in your browser from where you can get the generated auth_code
    generateTokenUrl = appSession.generate_authcode()
    print("generateTokenUrl: ",generateTokenUrl)

def automated_login(client_id,secret_key,FY_ID,TOTP_KEY,PIN,redirect_uri):

    pd.set_option('display.max_columns', None)
    warnings.filterwarnings('ignore')

    import base64


    def getEncodedString(string):
        string = str(string)
        base64_bytes = base64.b64encode(string.encode("ascii"))
        return base64_bytes.decode("ascii")

    global fyers,access_token

    URL_SEND_LOGIN_OTP = "https://api-t2.fyers.in/vagator/v2/send_login_otp_v2"
    res = requests.post(url=URL_SEND_LOGIN_OTP, json={"fy_id": getEncodedString(FY_ID), "app_id": "2"}).json()
    print(res)

    if datetime.now().second % 30 > 27: sleep(5)
    URL_VERIFY_OTP = "https://api-t2.fyers.in/vagator/v2/verify_otp"
    res2 = requests.post(url=URL_VERIFY_OTP,
                         json={"request_key": res["request_key"], "otp": pyotp.TOTP(TOTP_KEY).now()}).json()
    print(res2)

    ses = requests.Session()
    URL_VERIFY_OTP2 = "https://api-t2.fyers.in/vagator/v2/verify_pin_v2"
    payload2 = {"request_key": res2["request_key"], "identity_type": "pin", "identifier": getEncodedString(PIN)}
    res3 = ses.post(url=URL_VERIFY_OTP2, json=payload2).json()
    print("res3: ",res3)

    ses.headers.update({
        'authorization': f"Bearer {res3['data']['access_token']}"
    })

    TOKENURL = "https://api-t1.fyers.in/api/v3/token"
    payload3 = {"fyers_id": FY_ID,
                "app_id": client_id[:-4],
                "redirect_uri": redirect_uri,
                "appType": "100", "code_challenge": "",
                "state": "None", "scope": "", "nonce": "", "response_type": "code", "create_cookie": True}

    res3 = ses.post(url=TOKENURL, json=payload3).json()
    url = res3['Url']
    parsed = urlparse(url)
    auth_code = parse_qs(parsed.query)['auth_code'][0]
    grant_type = "authorization_code"

    response_type = "code"

    session = fyersModel.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type=response_type,
        grant_type=grant_type
    )
    session.set_token(auth_code)
    response = session.generate_token()
    access_token = response['access_token']
    print("access_token: ",access_token)
    fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path=os.getcwd())
    print(fyers.get_profile())

def get_ltp(SYMBOL):
    global fyers
    data={"symbols":f"{SYMBOL}"}
    res=fyers.quotes(data)
    if 'd' in res and len(res['d']) > 0:
        lp = res['d'][0]['v']['lp']
        return lp

    else:
        print("Last Price (lp) not found in the response.")




def get_position():
    global fyers
      ## This will provide all the trade related information
    res=fyers.positions()
    return res

def get_orderbook():
    global fyers
    res = fyers.orderbook()
    return res
      ## This will provide the user with all the order realted information


def place_order(symbol, qty, side, product_type="INTRADAY", order_type=1, limit_price=0):
    """
    Place an order on Fyers.
    symbol: e.g. NSE:NIFTY26MAR25000CE
    qty: int, lot size
    side: 1 = Buy, -1 = Sell
    product_type: INTRADAY (MIS) or MARGIN (NRML)
    order_type: 1 = Market, 2 = Limit
    limit_price: used when order_type=2
    Returns: API response dict with 'code', 'id', 'message', etc.
    """
    global fyers
    if fyers is None:
        return {"s": "error", "code": -1, "message": "Fyers not logged in"}
    try:
        data = {
            "symbol": symbol,
            "qty": int(qty),
            "type": int(order_type),
            "side": int(side),
            "productType": product_type,
            "limitPrice": float(limit_price) if order_type == 2 else 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        res = fyers.place_order(data=data)
        return res if isinstance(res, dict) else {"s": "error", "message": str(res)}
    except Exception as e:
        print(f"[FYERS] place_order failed for {symbol}: {e}")
        return {"s": "error", "code": -1, "message": str(e)}

def get_tradebook():
    global fyers
    res = fyers.tradebook()
    return res


def fetchOHLC_Daily(symbol):    # 30 days data
    try:
        dat =str(datetime.now().date())
        dat1 = str((datetime.now() - timedelta(50)).date())
        data = {
            "symbol": symbol,
            "resolution": "1D",
            "date_format": "1",
            "range_from": dat1,
            "range_to": dat ,
            "cont_flag": "1"
        }
        response = fyers.history(data=data)
        
        # Check if response is valid and has 'candles' key
        if not response or 'candles' not in response:
            print(f"[ERROR] fetchOHLC_Daily: Invalid response for {symbol}: {response}")
            return pd.DataFrame()  # Return empty DataFrame
        
        if not response['candles'] or len(response['candles']) == 0:
            print(f"[WARNING] fetchOHLC_Daily: No candles data for {symbol}")
            return pd.DataFrame()  # Return empty DataFrame
        
        cl = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = pd.DataFrame(response['candles'], columns=cl)
        df['date']=df['date'].apply(pd.Timestamp,unit='s',tzinfo=pytz.timezone('Asia/Kolkata'))
        return df
    except Exception as e:
        print(f"[ERROR] fetchOHLC_Daily failed for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()  # Return empty DataFrame on error

from datetime import datetime, timedelta
import pytz
import pandas as pd

from datetime import datetime, timedelta
import pytz
import pandas as pd

def fetchOHLC_Weekly(symbol):
    try:
        # Approx 140 days for 20 weeks of daily data
        dat = str(datetime.now().date())
        dat1 = str((datetime.now() - timedelta(days=350)).date())

        data = {
            "symbol": symbol,
            "resolution": "1D",
            "date_format": "1",
            "range_from": dat1,
            "range_to": dat,
            "cont_flag": "1"
        }

        response = fyers.history(data=data)
        # print("response weekly:", response)

        # Check if response is valid and has 'candles' key
        if not response or 'candles' not in response:
            print(f"[ERROR] fetchOHLC_Weekly: Invalid response for {symbol}: {response}")
            return pd.DataFrame()  # Return empty DataFrame
        
        if not response['candles'] or len(response['candles']) == 0:
            print(f"[WARNING] fetchOHLC_Weekly: No candles data for {symbol}")
            return pd.DataFrame()  # Return empty DataFrame

        cl = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = pd.DataFrame(response['candles'], columns=cl)

        # Convert Unix timestamp to datetime in IST
        df['date'] = pd.to_datetime(df['date'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        df.set_index('date', inplace=True)

        # Resample to weekly candles, week ending on Friday
        df_weekly = df.resample('W-FRI').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        # Drop incomplete weeks
        df_weekly.dropna(inplace=True)

        return df_weekly  # Return last 20 weeks
    except Exception as e:
        print(f"[ERROR] fetchOHLC_Weekly failed for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()  # Return empty DataFrame on error



def fetchOHLC(symbol,tf, max_retries=3, retry_delay=10):
    """
    Fetch OHLC data with retry logic for rate limit errors (429).
    
    According to Fyers API documentation:
    - To get completed candles only, subtract resolution time from range_to
    - Up to 100 days for minute resolutions (1, 2, 3, 5, 10, 15, 20, 30, 60, 120, 240)
    - Up to 366 days for 1D resolution
    - 30 trading days for seconds charts
    
    Args:
        symbol: Symbol to fetch data for
        tf: Timeframe (API format: '1D', '60', '15', '5S', etc.)
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Base delay in seconds between retries (default: 10)
    
    Returns:
        pandas DataFrame with OHLC data
    """
    for attempt in range(max_retries):
        try:
            print("symbol: ",symbol)
            
            # Get current datetime in IST timezone
            ist = pytz.timezone('Asia/Kolkata')
            now_ist = datetime.now(ist)
            
            # Determine date range based on resolution
            tf_str = str(tf).upper()
            
            # Check if it's daily resolution
            if tf_str == '1D' or tf_str == 'D':
                # Daily: up to 366 days, subtract 1 day from range_to for completed candles
                range_to = now_ist - timedelta(days=1)
                range_from = now_ist - timedelta(days=366)
            elif tf_str.endswith('S'):
                # Seconds: 30 trading days (approx 30 calendar days), subtract resolution seconds
                try:
                    seconds = int(tf_str[:-1])
                    range_to = now_ist - timedelta(seconds=seconds)
                    range_from = now_ist - timedelta(days=30)
                except ValueError:
                    # Fallback if seconds parsing fails
                    range_to = now_ist - timedelta(minutes=1)
                    range_from = now_ist - timedelta(days=30)
            else:
                # Minutes: up to 100 days, subtract resolution minutes from range_to
                try:
                    minutes = int(tf_str)
                    range_to = now_ist - timedelta(minutes=minutes)
                    range_from = now_ist - timedelta(days=100)
                except ValueError:
                    # Fallback if minutes parsing fails
                    range_to = now_ist - timedelta(minutes=1)
                    range_from = now_ist - timedelta(days=100)
            
            # Format dates as yyyy-mm-dd (date_format = 1)
            dat = str(range_to.date())
            dat1 = str(range_from.date())
            
            data = {
                "symbol": symbol,
                "resolution": str(tf),
                "date_format": "1",
                "range_from": dat1,
                "range_to": dat,
                "cont_flag": "1"
            }
            
            print(f"[FETCH] {symbol} ({tf}): range_from={dat1}, range_to={dat} (completed candles only)")
            response = fyers.history(data=data)
            # print("response: ",response)
            
            # Check for rate limit error (429)
            if isinstance(response, dict) and response.get('code') == 429:
                if attempt < max_retries - 1:
                    # Exponential backoff with longer delays: 10s, 20s, 30s
                    wait_time = retry_delay * (attempt + 1)
                    print(f"[RETRY] fetchOHLC: Rate limit reached for {symbol} ({tf}). Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                    sleep(wait_time)
                    continue  # Retry the request
                else:
                    print(f"[ERROR] fetchOHLC: Rate limit reached for {symbol} ({tf}) after {max_retries} attempts. Waiting 30 seconds before continuing...")
                    sleep(30)  # Wait longer before giving up and moving to next request
                    return pd.DataFrame()  # Return empty DataFrame after max retries
            
            # Check if response is valid and has 'candles' key
            if not response or 'candles' not in response:
                print(f"[ERROR] fetchOHLC: Invalid response for {symbol} ({tf}): {response}")
                return pd.DataFrame()  # Return empty DataFrame
            
            if not response['candles'] or len(response['candles']) == 0:
                print(f"[WARNING] fetchOHLC: No candles data for {symbol} ({tf})")
                return pd.DataFrame()  # Return empty DataFrame
            
            cl = ['date', 'open', 'high', 'low', 'close', 'volume']
            df = pd.DataFrame(response['candles'], columns=cl)
            df['date']=df['date'].apply(pd.Timestamp,unit='s',tzinfo=pytz.timezone('Asia/Kolkata'))
            return df
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"[RETRY] fetchOHLC: Exception for {symbol} ({tf}): {e}. Waiting {wait_time} seconds before retry {attempt + 2}/{max_retries}...")
                sleep(wait_time)
                continue  # Retry the request
            else:
                print(f"[ERROR] fetchOHLC failed for {symbol} ({tf}) after {max_retries} attempts: {e}")
                import traceback
                traceback.print_exc()
                return pd.DataFrame()  # Return empty DataFrame on error
    
    return pd.DataFrame()  # Fallback return


def fetchOHLC_get_selected_price(symbol, date):

    print("option symbol :",symbol)
    print("option symbol date :", date)
    dat = str(datetime.now().date())
    dat1 = str((datetime.now() - timedelta(25)).date())
    data = {
        "symbol": symbol,
        "resolution": "1D",
        "date_format": "1",
        "range_from": dat1,
        "range_to": dat,
        "cont_flag": "1"
    }
    response = fyers.history(data=data)
    cl = ['date', 'open', 'high', 'low', 'close', 'volume']
    df = pd.DataFrame(response['candles'], columns=cl)
    df['date'] = pd.to_datetime(df['date'], unit='s', utc=True).dt.tz_convert('Asia/Kolkata').dt.date
    target_date = pd.to_datetime(date).date()
    matching_row = df[df['date'] == target_date]
    if matching_row.empty:
        return 0
    else:
        close_price = matching_row.iloc[0]['close']
        return close_price
    



def fyres_websocket(symbollist):
    from fyers_apiv3.FyersWebsocket import data_ws
    global access_token

    def onmessage(message):
        """
        Callback function to handle incoming messages from the FyersDataSocket WebSocket.

        Parameters:
            message (dict): The received message from the WebSocket.

        """
        if 'symbol' in message and 'ltp' in message:
            symbol = message['symbol']
            ltp = message['ltp']
            shared_data[symbol] = ltp
            # Print live LTP stream for debugging/monitoring
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[LTP] {ts} | {symbol} -> {ltp}")




    def onerror(message):
        """
        Callback function to handle WebSocket errors.

        Parameters:
            message (dict): The error message received from the WebSocket.


        """
        print("Error:", message)


    def onclose(message):
        """
        Callback function to handle WebSocket connection close events.
        """
        print("Connection closed:", message)


    def onopen():
        """
        Callback function to subscribe to data type and symbols upon WebSocket connection.

        """
        # Specify the data type and symbols you want to subscribe to
        data_type = "SymbolUpdate"

        # Subscribe to the specified symbols and data type
        symbols = symbollist
        # ['NSE:LTIM24JULFUT', 'NSE:BHARTIARTL24JULFUT']
        fyers.subscribe(symbols=symbols, data_type=data_type)

        # Keep the socket running to receive real-time data
        fyers.keep_running()


    # Replace the sample access token with your actual access token obtained from Fyers
    # access_token = "XC4XXXXXXM-100:eXXXXXXXXXXXXfZNSBoLo"

    # Create a FyersDataSocket instance with the provided parameters
    fyers = data_ws.FyersDataSocket(
        access_token=access_token,  # Access token in the format "appid:accesstoken"
        log_path="",  # Path to save logs. Leave empty to auto-create logs in the current directory.
        litemode=True,  # Lite mode disabled. Set to True if you want a lite response.
        write_to_file=False,  # Save response in a log file instead of printing it.
        reconnect=True,  # Enable auto-reconnection to WebSocket on disconnection.
        on_connect=onopen,  # Callback function to subscribe to data upon connection.
        on_close=onclose,  # Callback function to handle WebSocket connection close events.
        on_error=onerror,  # Callback function to handle WebSocket errors.
        on_message=onmessage  # Callback function to handle incoming messages from the WebSocket.
    )

    # Establish a connection to the Fyers WebSocket
    fyers.connect()

def fyres_quote(symbol):
    data = {
        "symbols": f"{symbol}"
    }

    response = fyers.quotes(data=data)
    return response





def fyres_websocket_option(symbollist):
    from fyers_apiv3.FyersWebsocket import data_ws
    global access_token

    def onmessage(message):
        """
        Callback function to handle incoming messages from the FyersDataSocket WebSocket.

        Parameters:
            message (dict): The received message from the WebSocket.

        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - {message}\n")
        if 'symbol' in message and 'ltp' in message:
            shared_data_2[message['symbol']] = message['ltp']




    def onerror(message):
        """
        Callback function to handle WebSocket errors.

        Parameters:
            message (dict): The error message received from the WebSocket.


        """
        print("Error:", message)


    def onclose(message):
        """
        Callback function to handle WebSocket connection close events.
        """
        print("Connection closed:", message)


    def onopen():
        """
        Callback function to subscribe to data type and symbols upon WebSocket connection.

        """
        # Specify the data type and symbols you want to subscribe to
        data_type = "SymbolUpdate"

        # Subscribe to the specified symbols and data type
        symbols = symbollist
        # ['NSE:LTIM24JULFUT', 'NSE:BHARTIARTL24JULFUT']
        fyers.subscribe(symbols=symbols, data_type=data_type)

        # Keep the socket running to receive real-time data
        fyers.keep_running()


    # Replace the sample access token with your actual access token obtained from Fyers
    # access_token = "XC4XXXXXXM-100:eXXXXXXXXXXXXfZNSBoLo"

    # Create a FyersDataSocket instance with the provided parameters
    fyers = data_ws.FyersDataSocket(
        access_token=access_token,  # Access token in the format "appid:accesstoken"
        log_path="",  # Path to save logs. Leave empty to auto-create logs in the current directory.
        litemode=True,  # Lite mode disabled. Set to True if you want a lite response.
        write_to_file=False,  # Save response in a log file instead of printing it.
        reconnect=True,  # Enable auto-reconnection to WebSocket on disconnection.
        on_connect=onopen,  # Callback function to subscribe to data upon connection.
        on_close=onclose,  # Callback function to handle WebSocket connection close events.
        on_error=onerror,  # Callback function to handle WebSocket errors.
        on_message=onmessage  # Callback function to handle incoming messages from the WebSocket.
    )

    # Establish a connection to the Fyers WebSocket
    fyers.connect()

