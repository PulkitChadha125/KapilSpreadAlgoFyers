import csv
import os
import pandas as pd
import datetime as dt  # full module for timezone-safe operations
import math
import polars as pl
import polars_talib as plta
import json
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for

# from datetime import datetime, timedelta
import time
import traceback
import sys
from FyresIntegration import *
from datetime import datetime, timedelta



def get_api_credentials_Fyers():
    credentials_dict_fyers = {}
    try:
        df = pd.read_csv('FyersCredentials.csv')
        for index, row in df.iterrows():
            title = row['Title']
            value = row['Value']
            credentials_dict_fyers[title] = value
    except pd.errors.EmptyDataError:
        print("The CSV FyersCredentials.csv file is empty or has no data.")
    except FileNotFoundError:
        print("The CSV FyersCredentials.csv file was not found.")
    except Exception as e:
        print("An error occurred while reading the CSV FyersCredentials.csv file:", str(e))
    return credentials_dict_fyers



def delete_file_contents(file_name):
    try:
        # Open the file in write mode, which truncates it (deletes contents)
        with open(file_name, 'w') as file:
            file.truncate(0)
        print(f"Contents of {file_name} have been deleted.")
    except FileNotFoundError:
        print(f"File {file_name} not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

          

def write_to_order_logs(message):
    with open('OrderLog.txt', 'a') as file:  # Open the file in append mode
        file.write(message + '\n')




def get_user_settings():
    global result_dict, instrument_id_list, Equity_instrument_id_list, Future_instrument_id_list, FyerSymbolList
    from datetime import datetime
    import pandas as pd

    delete_file_contents("OrderLog.txt")

    try:
        csv_path = 'TradeSettings.csv'
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()

        result_dict = {}
        FyerSymbolList = []

        for index, row in df.iterrows():
            try:
                #Symbol,BaseSymbol,Quantity,StrikeRange,StrikeStep,PremiumUp,PremiumDown,Target,StopLoss,ExpType,StartTime,StopTime,TRADINGENABLED
                symbol     = str(row.get('Symbol', '')).strip()
                BaseSymbol = str(row.get('BaseSymbol', '')).strip()
                Quantity     = row.get('Quantity')  # 'dd-mm-YYYY' expected
                StrikeRange    = str(row.get('StrikeRange', '')).strip()
                StrikeStep = str(row.get('StrikeStep', '')).strip().upper()
                PremiumUp     = row.get('PremiumUp')
                PremiumDown    = row.get('PremiumDown')
                Target = row.get("Target")
                StopLoss = row.get("StopLoss")
                ExpType  = row.get("ExpType")
                StartTime   = row.get("StartTime")
                StopTime   = row.get("StopTime")
                TRADINGENABLED   = row.get("TRADINGENABLED")
                ExpieryDate   = row.get("ExpieryDate")
                print("-" * 50)
                print(f"symbol: {symbol}")
                print(f"BaseSymbol: {BaseSymbol}")  
                print(f"Quantity: {Quantity}")
                print(f"StrikeRange: {StrikeRange}")
                print(f"StrikeStep: {StrikeStep}")
                print(f"PremiumUp: {PremiumUp}")
                print(f"PremiumDown: {PremiumDown}")
                print(f"Target: {Target}")
                print(f"StopLoss: {StopLoss}")
                print(f"ExpType: {ExpType}")
                print(f"StartTime: {StartTime}")
                print(f"StopTime: {StopTime}")
                print(f"TRADINGENABLED: {TRADINGENABLED}")
                print(f"ExpieryDate: {ExpieryDate}")

                # --- Start/Stop time: robust parsing with defaults ---
                start_time_str = str(StartTime).strip() if pd.notna(StartTime) else "09:15"
                stop_time_str  = str(StopTime).strip()  if pd.notna(StopTime)  else "15:30"
                try:
                    start_time = datetime.strptime(start_time_str, "%H:%M").time()
                except Exception:
                    start_time = datetime.strptime("09:15", "%H:%M").time()
                try:
                    stop_time = datetime.strptime(stop_time_str, "%H:%M").time()
                except Exception:
                    stop_time = datetime.strptime("15:30", "%H:%M").time()

                # --- Quantity: you already like using int() here (kept) ---
                Quantity = int(Quantity)
                # --- Strike: normalize '24750.0' -> '24750' and keep as string ---
                if pd.notna(PremiumUp):
                    if isinstance(PremiumUp, (int, float)):
                        if float(PremiumUp).is_integer():
                            PremiumUp = str(int(PremiumUp))
                        else:
                            PremiumUp = str(PremiumUp).strip()
                    else:
                        PremiumUp = str(PremiumUp).strip()
                else:
                    PremiumUp = ""

                # --- Build Fyers symbol for Weekly/Monthly options (only if expiry present) ---
                # Note: Actual option symbol list is built in build_option_subscriptions(), not here.
                fyers_symbol = None
                if pd.notna(ExpieryDate):
                    expiry_str = str(ExpieryDate).strip()
                    if ExpType == "MONTHLY":
                        # e.g., '29-05-2025' -> '25MAY' (single symbol placeholder; full list built elsewhere)
                        expiry_date = datetime.strptime(expiry_str, '%d-%m-%Y')
                        new_date_string = expiry_date.strftime('%y%b').upper()
                        fyers_symbol = f"NSE:{BaseSymbol}{new_date_string}"
                    #     if symbol == "SENSEX":
                    #         fyers_symbol = f"BSE:{symbol}{new_date_string}{Strike}{OptionType}"
                    #     print(f"fyers_symbol: {fyers_symbol}")
                    # elif ExpType == "WEEKLY":
                    #     # e.g., '16-09-2025' -> YYMDD (25 9 16) => NIFTY2591624750CE
                    #     expiry_date = datetime.strptime(expiry_str, "%d-%m-%Y")
                    #     year_yy = expiry_date.strftime('%y')            # '25'
                    #     month_m = str(int(expiry_date.strftime('%m')))  # '9' (no leading zero)
                    #     day_dd = expiry_date.strftime('%d')            # '16'
                    #     expiry_formatted = f"{year_yy}{month_m}{day_dd}"
                    #     print(f"Weekly expiry from CSV: {expiry_formatted}")
                    #     fyers_symbol = f"NSE:{symbol}{expiry_formatted}{Strike}{OptionType}"
                    #     if symbol == "SENSEX":
                    #         fyers_symbol = f"BSE:{symbol}{new_date_string}{Strike}{OptionType}"
                    #     print(f"fyers_symbol: {fyers_symbol}")
                    

                else:
                    print(f"[WARN] Row {index}: missing EXPIERY; skipping symbol construction.")

                # --- Unique key (allows multiple rows per underlying) ---
                unique_key = f"{symbol}_{ExpType}_{ExpieryDate}"

                # --- Build symbol_dict (no extra casting for your fields) ---
                symbol_dict = {
                    "Symbol": symbol,
                    "BaseSymbol": BaseSymbol,
                    "unique_key": unique_key,
                    "Quantity": Quantity,
                    "StrikeRange": StrikeRange,
                    "StrikeStep": StrikeStep,
                    "PremiumUp": PremiumUp,
                    "PremiumDown": PremiumDown,
                    "Target": Target,
                    "StopLoss": StopLoss,
                    "ExpieryDate": ExpieryDate,
                    "ExpType": ExpType,
                    "StartTime": StartTime,
                    "StopTime": StopTime,
                    "TRADINGENABLED": TRADINGENABLED,
                }
            
            
            except Exception as e:
                print("Error happened in fetching symbol", str(e))  
                traceback.print_exc()
            print("symbol_dict: ", symbol_dict)
            print("-" * 50)
            result_dict.append(symbol_dict)

    except Exception as e:
        print("Error happened in fetching symbol", str(e))
        traceback.print_exc()
    return result_dict


app = Flask(__name__)

# Global containers for strategy
strategy_running = False
option_key_by_symbol = {}
FyerSymbolList = []
STATE_FILE = "state.json"
ORDER_LOG_FILE = "order_log.csv"
_last_no_strike_log = {}  # unique_key -> last log timestamp (throttle NO_STRIKE_IN_RANGE to once per 60s)
_last_login_date = None  # date of last successful Fyers login (IST)
_login_creds = {}        # cached credentials for automated_login

ORDER_LOG_COLUMNS = [
    "timestamp",
    "event",
    "strategy_key",
    "base_symbol",
    "symbol",
    "call_symbol",
    "put_symbol",
    "price_call",
    "price_put",
    "combined_price",
    "target_pct",
    "stop_pct",
    "target_abs",
    "stop_abs",
    "pnl_abs",
    "pnl_pct",
    "details",
    "ce_request",
    "ce_response",
    "pe_request",
    "pe_response",
]


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            raw = json.load(f)
            if not isinstance(raw, dict):
                return {}
            # Only keep entries that are actually in-position. This ensures
            # state.json semantically represents *open* positions only.
            clean = {}
            for key, rec in raw.items():
                if isinstance(rec, dict) and rec.get("in_position"):
                    clean[key] = rec
            # If we dropped anything (closed positions lingering from older runs),
            # write back the cleaned state so the file matches the in-memory view.
            if clean != raw:
                save_state(clean)
            return clean
    except FileNotFoundError:
        return {}
    except Exception as e:
        print("[STATE] Failed to read state.json:", e)
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print("[STATE] Failed to write state.json:", e)


def append_order_log(
    event: str,
    strategy_key: str = "",
    base_symbol: str | None = None,
    symbol: str | None = None,
    call_symbol: str | None = None,
    put_symbol: str | None = None,
    price_call: float | None = None,
    price_put: float | None = None,
    combined_price: float | None = None,
    target_pct: float | None = None,
    stop_pct: float | None = None,
    target_abs: float | None = None,
    stop_abs: float | None = None,
    pnl_abs: float | None = None,
    pnl_pct: float | None = None,
    details: str = "",
    ce_request: dict | None = None,
    ce_response: dict | None = None,
    pe_request: dict | None = None,
    pe_response: dict | None = None,
) -> None:
    """
    Append a single event to the CSV order log in a tabular, comma-separated format.
    """
    try:
        file_exists = os.path.exists(ORDER_LOG_FILE)
        with open(ORDER_LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=ORDER_LOG_COLUMNS)
            if not file_exists:
                writer.writeheader()

            # Use Indian Standard Time (IST, UTC+5:30) for all log timestamps
            utc_now = dt.datetime.utcnow()
            ist_now = utc_now + dt.timedelta(hours=5, minutes=30)
            now_ts = ist_now.strftime("%Y-%m-%dT%H:%M:%S")
            row = {
                "timestamp": now_ts,
                "event": event,
                "strategy_key": strategy_key,
                "base_symbol": base_symbol or "",
                "symbol": symbol or "",
                "call_symbol": call_symbol or "",
                "put_symbol": put_symbol or "",
                "price_call": "" if price_call is None else price_call,
                "price_put": "" if price_put is None else price_put,
                "combined_price": "" if combined_price is None else combined_price,
                "target_pct": "" if target_pct is None else target_pct,
                "stop_pct": "" if stop_pct is None else stop_pct,
                "target_abs": "" if target_abs is None else target_abs,
                "stop_abs": "" if stop_abs is None else stop_abs,
                "pnl_abs": "" if pnl_abs is None else pnl_abs,
                "pnl_pct": "" if pnl_pct is None else pnl_pct,
                "details": details,
                "ce_request": "" if ce_request is None else json.dumps(ce_request, ensure_ascii=False),
                "ce_response": "" if ce_response is None else json.dumps(ce_response, ensure_ascii=False),
                "pe_request": "" if pe_request is None else json.dumps(pe_request, ensure_ascii=False),
                "pe_response": "" if pe_response is None else json.dumps(pe_response, ensure_ascii=False),
            }
            writer.writerow(row)
    except Exception as e:
        print("[ORDER_LOG] Failed to append event:", e)


def load_trade_settings_df():
    """
    Helper used by the Flask UI to load TradeSettings.csv.
    """
    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        print("Error loading TradeSettings.csv for UI:", e)
        return pd.DataFrame()


@app.route("/")
def symbol_settings():
    """
    Symbol Settings page – shows all rows from TradeSettings.csv.
    """
    df = load_trade_settings_df()
    settings = df.to_dict(orient="records")
    return render_template("symbol_settings.html", settings=settings)


def _normalize_symbol_for_ltp(symbol: str) -> str:
    """
    Build a Fyers-compatible underlying symbol for LTP fetches.
    If the symbol already looks like a full Fyers symbol (contains ':'),
    it is returned as-is. Otherwise we assume an index and append '-INDEX'.
    """
    symbol = str(symbol).strip().upper()
    if ":" in symbol:
        return symbol
    # Heuristic: treat as NSE index
    return f"NSE:{symbol}-INDEX"


def build_option_subscriptions():
    """
    Build option symbol lists for each underlying based on TradeSettings.csv.

    For each enabled row:
      - fetch underlying LTP
      - round to nearest strike step to get ATM
      - generate strikes up/down by StrikeRange steps
      - format monthly option contracts for both CE and PE

    Populates:
      - option_key_by_symbol[symbol] = list of option symbols
      - FyerSymbolList = merged unique list of all option symbols
    """
    global option_key_by_symbol, FyerSymbolList

    option_key_by_symbol = {}
    FyerSymbolList = []

    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print("[STRATEGY] Failed to read TradeSettings.csv in build_option_subscriptions:", e)
        return

    for _, row in df.iterrows():
        try:
            symbol_raw = str(row.get("Symbol", "")).strip()
            base_symbol_raw = str(row.get("BaseSymbol", "")).strip()
            if not symbol_raw:
                continue

            symbol = symbol_raw.upper()
            base_symbol = base_symbol_raw.upper() if base_symbol_raw else symbol.split(":")[-1]

            # Detect exchange prefix from the symbol, default to NSE if missing.
            # Examples:
            #   NSE:NIFTY26MARFUT  -> prefix = "NSE"
            #   BSE:XYZ26MARFUT    -> prefix = "BSE"
            #   MCX:CRUDEOIL26MARFUT -> prefix = "MCX"
            if ":" in symbol_raw:
                prefix = symbol_raw.split(":", 1)[0].strip().upper()
            else:
                prefix = "NSE"

            trading_enabled = str(row.get("TRADINGENABLED", "TRUE")).strip().upper()
            if trading_enabled != "TRUE":
                continue

            strike_step_raw = row.get("StrikeStep", 50)
            try:
                strike_step = int(str(strike_step_raw).strip())
            except Exception:
                strike_step = 50

            strike_range_raw = row.get("StrikeRange", 0)
            try:
                strike_range = int(str(strike_range_raw).strip())
            except Exception:
                strike_range = 0

            if strike_range <= 0 or strike_step <= 0:
                print(f"[STRATEGY] Skipping {symbol}: invalid StrikeRange/StrikeStep ({strike_range}, {strike_step})")
                continue

            expiry_str = str(row.get("ExpieryDate", "")).strip()
            if not expiry_str:
                print(f"[STRATEGY] Skipping {symbol}: missing ExpieryDate")
                continue

            exp_type = str(row.get("ExpType", "MONTHLY")).strip().upper()
            if exp_type not in ("MONTHLY", "WEEKLY"):
                print(f"[STRATEGY] Skipping {symbol}: ExpType {exp_type} not supported (use MONTHLY or WEEKLY).")
                continue

            underlying_symbol = _normalize_symbol_for_ltp(symbol_raw)
            ltp = get_ltp(underlying_symbol)
            if ltp is None:
                print(f"[STRATEGY] No LTP for underlying {underlying_symbol}, skipping.")
                continue

            try:
                ltp_val = float(ltp)
            except Exception:
                print(f"[STRATEGY] Invalid LTP {ltp} for {underlying_symbol}, skipping.")
                continue

            # Round to nearest strike step to get ATM
            atm_strike = int(round(ltp_val / strike_step) * strike_step)

            strikes = []
            for i in range(-strike_range, strike_range + 1):
                strikes.append(atm_strike + i * strike_step)

            option_symbols = []
            try:
                expiry_date = datetime.strptime(expiry_str, "%d-%m-%Y")
            except Exception as e:
                print(f"[STRATEGY] Failed to parse expiry {expiry_str} for {symbol}: {e}")
                continue

            if exp_type == "MONTHLY":
                # Monthly: NSE:NIFTY26MAR25000CE (YY + MMM + strike + CE/PE)
                new_date_string = expiry_date.strftime("%y%b").upper()
            else:
                # Weekly: Fyers doc says {YY}{M}{dd} with M = 1-9 or O,N,D (e.g. NSE:NIFTY2640711000CE for 07-Apr-2026)
                yy = expiry_date.strftime("%y")
                mm = expiry_date.month
                month_char = str(mm) if 1 <= mm <= 9 else {10: "O", 11: "N", 12: "D"}[mm]
                dd = expiry_date.strftime("%d")
                new_date_string = f"{yy}{month_char}{dd}"

            unique_key = f"{symbol_raw.strip()}|{exp_type}|{expiry_str}"

            for strike in strikes:
                strike_int = int(strike)
                for opt_type in ("CE", "PE"):
                    fyers_symbol = f"{prefix}:{base_symbol}{new_date_string}{strike_int}{opt_type}"
                    option_symbols.append(fyers_symbol)

            option_key_by_symbol[unique_key] = option_symbols
            FyerSymbolList.extend(option_symbols)
            print(f"[STRATEGY] Built {len(option_symbols)} option symbols for {symbol} ({exp_type} {expiry_str})")

        except Exception as e:
            print(f"[STRATEGY] Error while building options for a row: {e}")
            traceback.print_exc()

    # Deduplicate while preserving order
    seen = set()
    unique_list = []
    for s in FyerSymbolList:
        if s not in seen:
            seen.add(s)
            unique_list.append(s)
    FyerSymbolList = unique_list
    print(f"[STRATEGY] Total unique option symbols in FyerSymbolList: {len(FyerSymbolList)}")


def _start_websocket_worker():
    global FyerSymbolList
    if not FyerSymbolList:
        print("[STRATEGY] No symbols in FyerSymbolList to subscribe to websocket.")
        return
    print("[STRATEGY] Starting websocket for symbols:", len(FyerSymbolList))
    fyres_websocket(FyerSymbolList)


def _strategy_loop_worker():
    """
    Simple loop that, once per second, logs the latest LTP for all subscribed options.
    Trading logic will plug into this later.
    """
    global strategy_running, FyerSymbolList, _last_login_date, _login_creds
    from FyresIntegration import shared_data  # latest LTPs from websocket

    while strategy_running:
        try:
            # Scheduled daily Fyers re-login at 09:00 IST using cached credentials.
            try:
                if _login_creds:
                    ist_now = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
                    ist_today = ist_now.date()
                    ist_time = ist_now.time()
                    if ist_time >= dt.time(9, 0) and (_last_login_date is None or _last_login_date < ist_today):
                        print(f"[LOGIN] Performing scheduled daily Fyers re-login at {ist_now.isoformat()}")
                        automated_login(**_login_creds)
                        _last_login_date = ist_today
            except Exception as re_login_err:
                print("[LOGIN] Scheduled daily re-login failed:", re_login_err)
                traceback.print_exc()

            now_ts = datetime.now()
            today = now_ts.date()
            current_time = now_ts.time()

            df = load_trade_settings_df()
            if df.empty:
                time.sleep(1)
                continue

            state = load_state()

            # Ensure we work with object types to avoid casting issues
            df = df.astype(object)

            for idx, row in df.iterrows():
                try:
                    symbol = str(row.get("Symbol", "")).strip()
                    base_symbol = str(row.get("BaseSymbol", "")).strip() or symbol.split(":")[-1]
                    if not symbol:
                        continue

                    trading_enabled = str(row.get("TRADINGENABLED", "TRUE")).strip().upper()
                    if trading_enabled != "TRUE":
                        continue

                    exp_type = str(row.get("ExpType", "MONTHLY")).strip().upper()
                    if exp_type not in ("MONTHLY", "WEEKLY"):
                        continue

                    expiry_str = str(row.get("ExpieryDate", "")).strip()
                    unique_key = f"{symbol}|{exp_type}|{expiry_str}"

                    start_time_str = str(row.get("StartTime", "")).strip() or "09:15"
                    stop_time_str = str(row.get("StopTime", "")).strip() or "15:30"
                    try:
                        start_time = datetime.strptime(start_time_str, "%H:%M").time()
                    except Exception:
                        start_time = datetime.strptime("09:15", "%H:%M").time()
                    try:
                        stop_time = datetime.strptime(stop_time_str, "%H:%M").time()
                    except Exception:
                        stop_time = datetime.strptime("15:30", "%H:%M").time()

                    target_pct_raw = row.get("Target", 0)
                    stop_pct_raw = row.get("StopLoss", 0)
                    try:
                        target_pct = float(target_pct_raw)
                    except Exception:
                        target_pct = 0.0
                    # Treat NaN or empty as 0 (i.e. "not provided")
                    if math.isnan(target_pct):
                        target_pct = 0.0
                    try:
                        stop_pct = float(stop_pct_raw)
                    except Exception:
                        stop_pct = 0.0
                    if math.isnan(stop_pct):
                        stop_pct = 0.0

                    try:
                        quantity = int(row.get("Quantity", 1) or 1)
                    except Exception:
                        quantity = 1
                    quantity = max(1, quantity)

                    srec = state.get(unique_key, {"in_position": False})

                    # Stop-time forced exit
                    if srec.get("in_position") and current_time >= stop_time:
                        print(f"[STRATEGY] Stop time exit for {unique_key}")
                        exit_qty = srec.get("quantity", 1)
                        ce_sym = srec.get("call_symbol")
                        pe_sym = srec.get("put_symbol")

                        ltp_ce = shared_data.get(ce_sym) if ce_sym else None
                        ltp_pe = shared_data.get(pe_sym) if pe_sym else None

                        price_ce = float(ltp_ce) if ltp_ce is not None else None
                        price_pe = float(ltp_pe) if ltp_pe is not None else None

                        # Compute combined LTP and P&L at stop time (per pair, not multiplied by qty)
                        exit_combined = None
                        if price_ce is not None and price_pe is not None:
                            exit_combined = price_ce + price_pe
                        elif price_ce is not None:
                            exit_combined = price_ce
                        elif price_pe is not None:
                            exit_combined = price_pe

                        entry_combined = float(srec.get("entry_combined") or 0.0)
                        pnl_abs = None
                        pnl_pct = None
                        if exit_combined is not None and entry_combined:
                            pnl_abs = exit_combined - entry_combined
                            pnl_pct = (pnl_abs / entry_combined) * 100.0

                        print(
                            f"[EXIT_STOPTIME] {unique_key} | "
                            f"CE={ce_sym} @{price_ce}, PE={pe_sym} @{price_pe}, "
                            f"entry_combined={entry_combined}, exit_combined={exit_combined}, "
                            f"pnl_abs={pnl_abs}, pnl_pct={pnl_pct}"
                        )

                        sell_ce = place_order(ce_sym, exit_qty, -1, order_type=1, limit_price=price_ce) if ce_sym else {}
                        sell_pe = place_order(pe_sym, exit_qty, -1, order_type=1, limit_price=price_pe) if pe_sym else {}
                        order_detail = f"CE sell: {sell_ce.get('message', sell_ce)}; PE sell: {sell_pe.get('message', sell_pe)}"
                        append_order_log(
                            event="EXIT_STOPTIME",
                            strategy_key=unique_key,
                            base_symbol=base_symbol,
                            symbol=srec.get("symbol", symbol),
                            call_symbol=ce_sym,
                            put_symbol=pe_sym,
                            price_call=price_ce,
                            price_put=price_pe,
                            combined_price=exit_combined,
                            target_pct=srec.get("target_pct"),
                            stop_pct=srec.get("stop_pct"),
                            target_abs=srec.get("target_abs"),
                            stop_abs=srec.get("stop_abs"),
                            pnl_abs=pnl_abs,
                            pnl_pct=pnl_pct,
                            # Keep details focused on raw API messages for CE/PE
                            details=order_detail,
                            ce_request=sell_ce.get("request"),
                            ce_response=sell_ce.get("response"),
                            pe_request=sell_pe.get("request"),
                            pe_response=sell_pe.get("response"),
                        )
                        # Position is fully closed; clear this strategy key from state
                        srec["in_position"] = False
                        _clear_state_for_key(state, unique_key)
                        df.at[idx, "TRADINGENABLED"] = "FALSE"
                        continue

                    # Outside start/stop window: do nothing
                    if not (start_time <= current_time <= stop_time):
                        continue

                    # Ensure we have option symbols built for this row (key = Symbol|ExpType|ExpieryDate)
                    option_list = option_key_by_symbol.get(unique_key)
                    if not option_list:
                        continue

                    # If not yet in position, build entry at first opportunity
                    if not srec.get("in_position"):
                        premium_up = row.get("PremiumUp")
                        premium_down = row.get("PremiumDown")
                        try:
                            prem_up = float(premium_up)
                        except Exception:
                            prem_up = float("inf")
                        try:
                            prem_down = float(premium_down)
                        except Exception:
                            prem_down = 0.0

                        best_ce = None
                        best_ce_price = None
                        best_pe = None
                        best_pe_price = None

                        for opt_symbol in option_list:
                            ltp = shared_data.get(opt_symbol)
                            if ltp is None:
                                continue
                            try:
                                price = float(ltp)
                            except Exception:
                                continue

                            # Print per-symbol LTP used for entry decisions
                            print(f"[LTP] {unique_key} | {opt_symbol} -> {price}")

                            if not (prem_down <= price <= prem_up):
                                continue

                            if opt_symbol.endswith("CE"):
                                if best_ce_price is None or price < best_ce_price:
                                    best_ce_price = price
                                    best_ce = opt_symbol
                            elif opt_symbol.endswith("PE"):
                                if best_pe_price is None or price < best_pe_price:
                                    best_pe_price = price
                                    best_pe = opt_symbol

                        if not (best_ce and best_pe):
                            # Always check entry condition every tick (1 second) and print to console,
                            # but throttle CSV logging to once per 60s per strategy key.
                            reason = []
                            if not best_ce:
                                reason.append("no CE")
                            if not best_pe:
                                reason.append("no PE")

                            # Console message every second while no strike is in range
                            print(
                                f"[NO_STRIKE_IN_RANGE] {unique_key} | "
                                f"range [{prem_down}, {prem_up}] | missing: {', '.join(reason)}"
                            )

                            # CSV/order_log entry at most once per 60 seconds
                            now_sec = time.time()
                            last = _last_no_strike_log.get(unique_key, 0)
                            if now_sec - last >= 60:
                                _last_no_strike_log[unique_key] = now_sec
                                # Extra visual separator in console when we also log to CSV
                                print("\n" + "=" * 80)
                                print(
                                    f"[NO_STRIKE_IN_RANGE LOGGED] {unique_key} | "
                                    f"range [{prem_down}, {prem_up}] | missing: {', '.join(reason)}"
                                )
                                print("=" * 80 + "\n")
                                append_order_log(
                                    event="NO_STRIKE_IN_RANGE",
                                    strategy_key=unique_key,
                                    base_symbol=base_symbol,
                                    symbol=symbol,
                                    details=f"No strike in premium range [{prem_down}, {prem_up}] for {base_symbol}. Missing: {', '.join(reason)}. Waiting for LTP in range.",
                                )
                            continue

                        if best_ce and best_pe:
                            entry_combined = best_ce_price + best_pe_price
                            target_abs = entry_combined * (target_pct / 100.0)
                            stop_abs = entry_combined * (stop_pct / 100.0)

                            print(
                                f"[STRATEGY] ENTRY for {unique_key}: "
                                f"CE={best_ce} @{best_ce_price}, "
                                f"PE={best_pe} @{best_pe_price}, "
                                f"combined={entry_combined}, "
                                f"target+{target_abs} ({target_pct}%), "
                                f"stop-{stop_abs} ({stop_pct}%)"
                            )

                            # Place BUY orders on Fyers using LTP as limit price (LIMIT orders)
                            order_ce = place_order(best_ce, quantity, 1, order_type=1, limit_price=best_ce_price)
                            order_pe = place_order(best_pe, quantity, 1, order_type=1, limit_price=best_pe_price)
                            order_detail = f"CE order: {order_ce.get('message', order_ce)}; PE order: {order_pe.get('message', order_pe)}"
                            if order_ce.get("id"):
                                order_detail += f" [CE id={order_ce.get('id')}]"
                            if order_pe.get("id"):
                                order_detail += f" [PE id={order_pe.get('id')}]"

                            append_order_log(
                                event="ENTRY",
                                strategy_key=unique_key,
                                base_symbol=base_symbol,
                                symbol=symbol,
                                call_symbol=best_ce,
                                put_symbol=best_pe,
                                price_call=best_ce_price,
                                price_put=best_pe_price,
                                combined_price=entry_combined,
                                target_pct=target_pct,
                                stop_pct=stop_pct,
                                target_abs=target_abs,
                                stop_abs=stop_abs,
                                details=f"Placed BUY orders on Fyers (qty={quantity}). {order_detail}",
                                ce_request=order_ce.get("request"),
                                ce_response=order_ce.get("response"),
                                pe_request=order_pe.get("request"),
                                pe_response=order_pe.get("response"),
                            )

                            # Treat this as an "entry" on the strategy side even if the broker
                            # rejects due to margin or lot-size errors. This is useful for
                            # testing the strategy logic independently of live broker status.
                            # Use a fresh state dict for this position so we never carry over stale
                            # entry_combined/target_abs from a previous cycle.
                            state[unique_key] = {
                                "symbol": symbol,
                                "base_symbol": base_symbol,
                                "call_symbol": best_ce,
                                "put_symbol": best_pe,
                                "entry_call": best_ce_price,
                                "entry_put": best_pe_price,
                                "entry_combined": entry_combined,
                                "target_pct": target_pct,
                                "stop_pct": stop_pct,
                                "target_abs": target_abs,
                                "stop_abs": stop_abs,
                                "quantity": quantity,
                                "in_position": True,
                                "entry_ts": datetime.now().isoformat(),
                            }
                        continue

                    # If already in position, monitor for target / stop-loss
                    if srec.get("in_position"):
                        ce_sym = srec.get("call_symbol")
                        pe_sym = srec.get("put_symbol")
                        if not ce_sym or not pe_sym:
                            continue

                        ltp_ce = shared_data.get(ce_sym)
                        ltp_pe = shared_data.get(pe_sym)
                        if ltp_ce is None or ltp_pe is None:
                            continue

                        try:
                            price_ce = float(ltp_ce)
                            price_pe = float(ltp_pe)
                        except Exception:
                            continue

                        combined = price_ce + price_pe
                        entry_call = srec.get("entry_call")
                        entry_put = srec.get("entry_put")
                        entry_combined = srec.get("entry_combined", combined)

                        # Detect live updates to Target/StopLoss in TradeSettings.csv
                        old_target_pct = float(srec.get("target_pct", 0.0) or 0.0)
                        old_stop_pct = float(srec.get("stop_pct", 0.0) or 0.0)
                        if math.isnan(old_target_pct):
                            old_target_pct = 0.0
                        if math.isnan(old_stop_pct):
                            old_stop_pct = 0.0

                        new_target_pct = 0.0 if math.isnan(target_pct) else target_pct
                        new_stop_pct = 0.0 if math.isnan(stop_pct) else stop_pct

                        if (new_target_pct != old_target_pct) or (new_stop_pct != old_stop_pct):
                            # Always calculate new absolute targets from the ORIGINAL
                            # entry combined premium, not from the latest market price.
                            new_target_abs = entry_combined * (new_target_pct / 100.0) if new_target_pct > 0 else 0.0
                            new_stop_abs = entry_combined * (new_stop_pct / 100.0) if new_stop_pct > 0 else 0.0

                            append_order_log(
                                event="TARGET_STOPLOSS_UPDATED",
                                strategy_key=unique_key,
                                base_symbol=base_symbol,
                                symbol=symbol,
                                call_symbol=ce_sym,
                                put_symbol=pe_sym,
                                # Show the original entry prices in the "modified"
                                # event so the log is anchored to the entry snapshot.
                                price_call=entry_call,
                                price_put=entry_put,
                                combined_price=entry_combined,
                                target_pct=new_target_pct,
                                stop_pct=new_stop_pct,
                                target_abs=new_target_abs,
                                stop_abs=new_stop_abs,
                                details=(
                                    f"Targets updated while trade open. "
                                    f"Old target={old_target_pct}%, new target={new_target_pct}%, "
                                    f"old stop={old_stop_pct}%, new stop={new_stop_pct}%."
                                ),
                            )

                            srec["target_pct"] = new_target_pct
                            srec["stop_pct"] = new_stop_pct
                            srec["target_abs"] = new_target_abs
                            srec["stop_abs"] = new_stop_abs

                        target_abs = float(srec.get("target_abs", 0.0) or 0.0)
                        stop_abs = float(srec.get("stop_abs", 0.0) or 0.0)

                        if combined >= entry_combined + target_abs and target_abs > 0:
                            print(
                                f"[STRATEGY] TARGET hit for {unique_key}: "
                                f"combined={combined} >= {entry_combined + target_abs}"
                            )
                            exit_qty = srec.get("quantity", 1)
                            sell_ce = place_order(ce_sym, exit_qty, -1, order_type=1, limit_price=price_ce)
                            sell_pe = place_order(pe_sym, exit_qty, -1, order_type=1, limit_price=price_pe)
                            order_detail = f"CE sell: {sell_ce.get('message', sell_ce)}; PE sell: {sell_pe.get('message', sell_pe)}"

                            pnl_abs = combined - entry_combined if entry_combined else None
                            pnl_pct = (pnl_abs / entry_combined) * 100.0 if (pnl_abs is not None and entry_combined) else None

                            append_order_log(
                                event="EXIT_TARGET",
                                strategy_key=unique_key,
                                base_symbol=base_symbol,
                                symbol=symbol,
                                call_symbol=ce_sym,
                                put_symbol=pe_sym,
                                price_call=price_ce,
                                price_put=price_pe,
                                combined_price=combined,
                                target_pct=srec.get("target_pct"),
                                stop_pct=srec.get("stop_pct"),
                                target_abs=target_abs,
                                stop_abs=stop_abs,
                                pnl_abs=pnl_abs,
                                pnl_pct=pnl_pct,
                                details=order_detail,
                                ce_request=sell_ce.get("request"),
                                ce_response=sell_ce.get("response"),
                                pe_request=sell_pe.get("request"),
                                pe_response=sell_pe.get("response"),
                            )
                            # Target hit; clear this strategy key so a future re-enable starts fresh
                            srec["in_position"] = False
                            _clear_state_for_key(state, unique_key)
                            df.at[idx, "TRADINGENABLED"] = "FALSE"
                        elif combined <= entry_combined - stop_abs and stop_abs > 0:
                            print(
                                f"[STRATEGY] STOP-LOSS hit for {unique_key}: "
                                f"combined={combined} <= {entry_combined - stop_abs}"
                            )
                            exit_qty = srec.get("quantity", 1)
                            sell_ce = place_order(ce_sym, exit_qty, -1, order_type=1, limit_price=price_ce)
                            sell_pe = place_order(pe_sym, exit_qty, -1, order_type=1, limit_price=price_pe)
                            order_detail = f"CE sell: {sell_ce.get('message', sell_ce)}; PE sell: {sell_pe.get('message', sell_pe)}"

                            pnl_abs = combined - entry_combined if entry_combined else None
                            pnl_pct = (pnl_abs / entry_combined) * 100.0 if (pnl_abs is not None and entry_combined) else None

                            append_order_log(
                                event="EXIT_STOPLOSS",
                                strategy_key=unique_key,
                                base_symbol=base_symbol,
                                symbol=symbol,
                                call_symbol=ce_sym,
                                put_symbol=pe_sym,
                                price_call=price_ce,
                                price_put=price_pe,
                                combined_price=combined,
                                target_pct=srec.get("target_pct"),
                                stop_pct=srec.get("stop_pct"),
                                target_abs=target_abs,
                                stop_abs=stop_abs,
                                pnl_abs=pnl_abs,
                                pnl_pct=pnl_pct,
                                details=order_detail,
                                ce_request=sell_ce.get("request"),
                                ce_response=sell_ce.get("response"),
                                pe_request=sell_pe.get("request"),
                                pe_response=sell_pe.get("response"),
                            )
                            # Stop-loss hit; clear this strategy key so a future re-enable starts fresh
                            srec["in_position"] = False
                            _clear_state_for_key(state, unique_key)
                            df.at[idx, "TRADINGENABLED"] = "FALSE"

                except Exception as inner_e:
                    print("[STRATEGY] Error in loop for a row:", inner_e)
                    traceback.print_exc()

            # Persist any state/CSV changes for this tick
            save_state(state)
            try:
                df.to_csv("TradeSettings.csv", index=False)
            except Exception as e:
                print("[STRATEGY] Failed to write TradeSettings.csv in loop:", e)

            snapshot_count = len(FyerSymbolList)
            print(f"[STRATEGY TICK] {now_ts} | tracking {snapshot_count} option symbols.")
            time.sleep(1)

        except Exception as loop_e:
            print("[STRATEGY] Unexpected error in strategy loop:", loop_e)
            traceback.print_exc()
            time.sleep(2)


@app.route("/strategy-status", methods=["GET"])
def strategy_status():
    """
    Return whether strategy is currently running, plus symbol count.
    """
    return jsonify({"running": strategy_running, "symbols": len(FyerSymbolList)})


@app.route("/strategy-positions", methods=["GET"])
def strategy_positions():
    """
    Return a lightweight view of open positions created by the strategy
    based on the state.json snapshot.
    """
    from FyresIntegration import shared_data  # latest LTPs from websocket

    state = load_state()
    positions = []
    for key, rec in state.items():
        if not isinstance(rec, dict):
            continue
        if not rec.get("in_position"):
            continue

        ce_sym = rec.get("call_symbol")
        pe_sym = rec.get("put_symbol")

        ltp_ce = shared_data.get(ce_sym) if ce_sym else None
        ltp_pe = shared_data.get(pe_sym) if pe_sym else None

        realized_pnl = None
        realized_pnl_pct = None
        try:
            qty = int(rec.get("quantity", 1) or 1)
        except Exception:
            qty = 1

        entry_call = rec.get("entry_call")
        entry_put = rec.get("entry_put")

        try:
            if (
                ltp_ce is not None
                and ltp_pe is not None
                and entry_call is not None
                and entry_put is not None
            ):
                price_ce = float(ltp_ce)
                price_pe = float(ltp_pe)
                e_ce = float(entry_call)
                e_pe = float(entry_put)
                # Realized P&L per leg = (current - entry) * quantity
                realized_ce = (price_ce - e_ce) * qty
                realized_pe = (price_pe - e_pe) * qty
                realized_pnl = realized_ce + realized_pe

                entry_combined = float(rec.get("entry_combined") or (e_ce + e_pe))
                notional = entry_combined * qty if entry_combined and qty else 0
                if notional:
                    realized_pnl_pct = (realized_pnl / notional) * 100.0
        except Exception:
            realized_pnl = None
            realized_pnl_pct = None

        positions.append(
            {
                "key": key,
                "base_symbol": rec.get("base_symbol"),
                "symbol": rec.get("symbol"),
                "call_symbol": rec.get("call_symbol"),
                "put_symbol": rec.get("put_symbol"),
                "entry_call": rec.get("entry_call"),
                "entry_put": rec.get("entry_put"),
                "entry_combined": rec.get("entry_combined"),
                "target_pct": rec.get("target_pct"),
                "stop_pct": rec.get("stop_pct"),
                "target_abs": rec.get("target_abs"),
                "stop_abs": rec.get("stop_abs"),
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct,
            }
        )

    return jsonify(positions)


@app.route("/start-strategy", methods=["POST"])
def start_strategy():
    """
    Start strategy:
      - login to Fyers
      - build option symbol lists from TradeSettings
      - start websocket subscription
      - start background strategy loop
    """
    global strategy_running, _login_creds, _last_login_date

    if strategy_running:
        return jsonify({"ok": True, "message": "Strategy already running"})

    creds = get_api_credentials_Fyers()
    redirect_uri = creds.get("redirect_uri")
    client_id = creds.get("client_id")
    secret_key = creds.get("secret_key")
    TOTP_KEY = creds.get("totpkey")
    FY_ID = creds.get("FY_ID")
    PIN = creds.get("PIN")

    # Cache credentials for scheduled daily re-login at 09:00 IST
    _login_creds = {
        "client_id": client_id,
        "secret_key": secret_key,
        "FY_ID": FY_ID,
        "TOTP_KEY": TOTP_KEY,
        "PIN": PIN,
        "redirect_uri": redirect_uri,
    }

    automated_login(**_login_creds)
    # Remember today's login date in IST so the 09:00 IST scheduler can compare correctly.
    ist_now = dt.datetime.utcnow() + dt.timedelta(hours=5, minutes=30)
    _last_login_date = ist_now.date()

    build_option_subscriptions()

    import threading

    threading.Thread(target=_start_websocket_worker, daemon=True).start()
    strategy_running = True
    threading.Thread(target=_strategy_loop_worker, daemon=True).start()

    return jsonify({"ok": True, "symbols": len(FyerSymbolList)})


@app.route("/stop-strategy", methods=["POST"])
def stop_strategy():
    """
    Stop the strategy loop. (Websocket is not explicitly closed yet.)
    """
    global strategy_running
    strategy_running = False
    return jsonify({"ok": True})


@app.route("/exit-all", methods=["POST"])
def exit_all():
    """
    Exit All: close strategy positions (place SELL orders) and log. Optional ?symbol= or body.symbol to exit only that symbol.
    """
    payload = request.get_json(silent=True) or {}
    filter_symbol = (payload.get("symbol") or request.args.get("symbol") or "").strip()

    state = load_state()
    exited = []
    for key, srec in list(state.items()):
        if not isinstance(srec, dict) or not srec.get("in_position"):
            continue
        if filter_symbol and srec.get("symbol", "").strip() != filter_symbol and srec.get("base_symbol", "").strip() != filter_symbol:
            continue
        ce_sym = srec.get("call_symbol")
        pe_sym = srec.get("put_symbol")
        qty = srec.get("quantity", 1)

        # Use latest LTP as limit price for manual exits as well
        from FyresIntegration import shared_data as _shared_data_exit_all
        ltp_ce = _shared_data_exit_all.get(ce_sym) if ce_sym else None
        ltp_pe = _shared_data_exit_all.get(pe_sym) if pe_sym else None
        price_ce = float(ltp_ce) if ltp_ce is not None else None
        price_pe = float(ltp_pe) if ltp_pe is not None else None

        exit_combined = None
        if price_ce is not None and price_pe is not None:
            exit_combined = price_ce + price_pe
        elif price_ce is not None:
            exit_combined = price_ce
        elif price_pe is not None:
            exit_combined = price_pe

        entry_combined = float(srec.get("entry_combined") or 0.0)
        pnl_abs = None
        pnl_pct = None
        if exit_combined is not None and entry_combined:
            pnl_abs = exit_combined - entry_combined
            pnl_pct = (pnl_abs / entry_combined) * 100.0

        sell_ce = place_order(ce_sym, qty, -1, order_type=1, limit_price=price_ce) if ce_sym else {}
        sell_pe = place_order(pe_sym, qty, -1, order_type=1, limit_price=price_pe) if pe_sym else {}
        order_detail = f"CE sell: {sell_ce.get('message', sell_ce)}; PE sell: {sell_pe.get('message', sell_pe)}"
        append_order_log(
            event="MANUAL_EXIT",
            strategy_key=key,
            base_symbol=srec.get("base_symbol"),
            symbol=srec.get("symbol"),
            call_symbol=ce_sym,
            put_symbol=pe_sym,
            price_call=price_ce,
            price_put=price_pe,
            combined_price=exit_combined,
            target_pct=srec.get("target_pct"),
            stop_pct=srec.get("stop_pct"),
            pnl_abs=pnl_abs,
            pnl_pct=pnl_pct,
            details=order_detail,
            ce_request=sell_ce.get("request"),
            ce_response=sell_ce.get("response"),
            pe_request=sell_pe.get("request"),
            pe_response=sell_pe.get("response"),
        )
        # Manual Exit All: position is closed, so clear the strategy key from state
        srec["in_position"] = False
        _clear_state_for_key(state, key)
        exited.append(key)

    if exited:
        save_state(state)
        _disable_trading_for_keys(exited)

    print(f"[UI] Exit All: closed {len(exited)} position(s): {exited}")
    # Return JSON so front-ends can immediately react without errors
    return jsonify({"ok": True, "exited": exited})


def _disable_trading_for_keys(keys):
    """Set TRADINGENABLED=FALSE in TradeSettings.csv for rows matching the given strategy keys (Symbol|ExpType|ExpieryDate)."""
    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
    except Exception:
        return
    for key in keys:
        parts = key.split("|")
        if len(parts) != 3:
            continue
        sym, exp_type, expiry = parts[0].strip(), parts[1].strip(), parts[2].strip()
        mask = (
            (df["Symbol"].astype(str).str.strip() == sym)
            & (df["ExpType"].astype(str).str.strip().str.upper() == exp_type.upper())
            & (df["ExpieryDate"].astype(str).str.strip() == expiry)
        )
        if mask.any():
            # TRADINGENABLED may be bool or string; assign a proper bool False
            # so pandas doesn't error when the column dtype is boolean.
            df.loc[mask, "TRADINGENABLED"] = False
    try:
        df.to_csv("TradeSettings.csv", index=False)
    except Exception as e:
        print("[UI] Failed to update TradeSettings.csv in _disable_trading_for_keys:", e)


def _clear_state_for_key(state: dict, key: str) -> None:
    """
    Remove a strategy key from the in-memory state dict when its position is closed.
    """
    try:
        if key in state:
            del state[key]
    except Exception as e:
        print(f"[STATE] Failed to clear state for key {key}:", e)


def _clear_state_for_symbol(symbol: str) -> None:
    """
    Clear all state entries for a given symbol (disable → enable).
    State keys are "Symbol|ExpType|ExpieryDate"; we remove any key starting with symbol + "|"
    so the next entry uses fresh LTP and computed target/stop.
    """
    try:
        state = load_state()
        prefix = symbol.strip() + "|"
        keys_to_del = [k for k in state if isinstance(k, str) and k.startswith(prefix)]
        for k in keys_to_del:
            del state[k]
        if keys_to_del:
            save_state(state)
            print(f"[STATE] Cleared state for symbol {symbol!r}: keys {keys_to_del}")
    except Exception as e:
        print(f"[STATE] Failed to clear state for symbol {symbol!r}:", e)


@app.route("/toggle-trading", methods=["POST"])
def toggle_trading():
    """
    Toggle TRADINGENABLED (TRUE/FALSE) for a given symbol in TradeSettings.csv.

    This updates the CSV on disk and returns the new boolean flag so that
    the front-end can refresh the UI for that symbol.
    """
    payload = request.get_json(silent=True) or {}
    symbol = str(payload.get("symbol", "")).strip()

    if not symbol:
        return jsonify({"error": "symbol is required"}), 400

    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print("[UI] Failed to read TradeSettings.csv in toggle_trading:", e)
        return jsonify({"error": "failed to read TradeSettings.csv"}), 500

    if "Symbol" not in df.columns or "TRADINGENABLED" not in df.columns:
        return jsonify({"error": "TradeSettings.csv missing required columns"}), 500

    # Ensure TRADINGENABLED is a string column with TRUE/FALSE values
    df["TRADINGENABLED"] = df["TRADINGENABLED"].astype(str).str.upper()

    mask = df["Symbol"].astype(str).str.strip() == symbol
    if not mask.any():
        return jsonify({"error": f"symbol {symbol} not found"}), 404

    current_raw = str(df.loc[mask, "TRADINGENABLED"].iloc[0]).upper()
    new_raw = "FALSE" if current_raw == "TRUE" else "TRUE"

    # Broadcast scalar string to all matching rows
    df.loc[mask, "TRADINGENABLED"] = new_raw

    try:
        df.to_csv("TradeSettings.csv", index=False)
    except Exception as e:
        print("[UI] Failed to write TradeSettings.csv in toggle_trading:", e)
        return jsonify({"error": "failed to write TradeSettings.csv"}), 500

    # When turning disabled → enabled, clear state for this symbol so the next entry
    # uses fresh LTP and computed target/stop (no stale entry/target from previous cycle).
    if new_raw == "TRUE":
        _clear_state_for_symbol(symbol)

    new_enabled = new_raw == "TRUE"
    print(f"[UI] Toggle trading for {symbol}: {current_raw} -> {new_raw}")
    return jsonify({"symbol": symbol, "tradingEnabled": new_enabled, "tradingEnabledRaw": new_raw})


@app.route("/delete-setting", methods=["POST"])
def delete_setting():
    """
    Delete all rows in TradeSettings.csv for a given symbol.
    """
    payload = request.get_json(silent=True) or {}
    symbol = str(payload.get("symbol", "")).strip()

    if not symbol:
        return jsonify({"error": "symbol is required"}), 400

    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print("[UI] Failed to read TradeSettings.csv in delete_setting:", e)
        return jsonify({"error": "failed to read TradeSettings.csv"}), 500

    if "Symbol" not in df.columns:
        return jsonify({"error": "TradeSettings.csv missing Symbol column"}), 500

    mask = df["Symbol"].astype(str).str.strip() == symbol
    if not mask.any():
        return jsonify({"error": f"symbol {symbol} not found"}), 404

    df = df.loc[~mask].copy()

    try:
        df.to_csv("TradeSettings.csv", index=False)
    except Exception as e:
        print("[UI] Failed to write TradeSettings.csv in delete_setting:", e)
        return jsonify({"error": "failed to write TradeSettings.csv"}), 500

    print(f"[UI] Deleted settings for symbol: {symbol}")
    return ("", 204)


@app.route("/import-settings", methods=["POST"])
def import_settings():
    """
    Import TradeSettings from an uploaded CSV file.
    The CSV must match the existing TradeSettings.csv column structure.
    """
    file = request.files.get("file")
    if not file or file.filename == "":
        print("[UI] No file provided to import-settings.")
        return redirect(url_for("symbol_settings"))

    try:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print("[UI] Failed to parse uploaded CSV in import_settings:", e)
        return redirect(url_for("symbol_settings"))

    required_cols = [
        "Symbol",
        "Quantity",
        "StrikeRange",
        "StrikeStep",
        "PremiumUp",
        "PremiumDown",
        "Target",
        "StopLoss",
        "ExpieryDate",
        "ExpType",
        "StartTime",
        "StopTime",
        "TRADINGENABLED",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"[UI] Uploaded CSV missing columns: {missing}")
        return redirect(url_for("symbol_settings"))

    try:
        df.to_csv("TradeSettings.csv", index=False)
        print("[UI] TradeSettings.csv successfully replaced via import.")
    except Exception as e:
        print("[UI] Failed to write TradeSettings.csv in import_settings:", e)

    return redirect(url_for("symbol_settings"))


@app.route("/export-settings", methods=["GET"])
def export_settings():
    """
    Export the current TradeSettings.csv as a downloadable file.
    """
    try:
        return send_file(
            "TradeSettings.csv",
            mimetype="text/csv",
            as_attachment=True,
            download_name="TradeSettings.csv",
        )
    except Exception as e:
        print("[UI] Failed to send TradeSettings.csv in export_settings:", e)
        return redirect(url_for("symbol_settings"))


@app.route("/save-setting", methods=["POST"])
def save_setting():
    """
    Create or update a single row in TradeSettings.csv.

    If a row exists with the same (Symbol, ExpType, ExpieryDate),
    it is updated; otherwise, a new row is appended.
    """
    payload = request.get_json(silent=True) or {}

    symbol = str(payload.get("Symbol", "")).strip()
    if not symbol:
        return jsonify({"error": "Symbol is required"}), 400

    # Read existing CSV or create a new DataFrame if it doesn't exist
    try:
        df = pd.read_csv("TradeSettings.csv")
        df.columns = df.columns.str.strip()
    except FileNotFoundError:
        df = pd.DataFrame(
            columns=[
                "Symbol",
                "BaseSymbol",
                "Quantity",
                "StrikeRange",
                "StrikeStep",
                "PremiumUp",
                "PremiumDown",
                "Target",
                "StopLoss",
                "ExpieryDate",
                "ExpType",
                "StartTime",
                "StopTime",
                "TRADINGENABLED",
            ]
        )
    except Exception as e:
        print("[UI] Failed to read TradeSettings.csv in save_setting:", e)
        return jsonify({"error": "failed to read TradeSettings.csv"}), 500

    # Work with object dtype to avoid strict numeric casting issues when updating
    df = df.astype(object)

    # Normalize / convert fields
    base_symbol = str(payload.get("BaseSymbol", "")).strip()
    quantity = payload.get("Quantity")
    try:
        quantity = int(quantity) if quantity not in (None, "") else ""
    except Exception:
        quantity = quantity

    strike_range = str(payload.get("StrikeRange", "")).strip()
    strike_step = str(payload.get("StrikeStep", "")).strip()
    premium_up = payload.get("PremiumUp")
    premium_down = payload.get("PremiumDown")
    target = payload.get("Target")
    stop_loss = payload.get("StopLoss")

    exp_type = str(payload.get("ExpType", "MONTHLY")).strip().upper()
    if exp_type not in ("MONTHLY", "WEEKLY"):
        exp_type = "MONTHLY"

    raw_date = str(payload.get("ExpieryDate", "")).strip()
    ex_date_out = ""
    if raw_date:
        # raw_date is expected as YYYY-MM-DD from <input type="date">
        try:
            dt = datetime.strptime(raw_date, "%Y-%m-%d")
            ex_date_out = dt.strftime("%d-%m-%Y")
        except Exception:
            ex_date_out = raw_date

    original_raw_date = str(payload.get("OriginalExpieryDate", "")).strip()
    original_ex_date = original_raw_date or ex_date_out

    original_symbol = str(payload.get("OriginalSymbol", "")).strip()
    key_symbol = original_symbol or symbol

    # Use ORIGINAL ExpType to find the row when user edits expiry type/date (avoids duplicates)
    original_exp_type_raw = str(payload.get("OriginalExpType", "")).strip().upper()
    original_exp_type = original_exp_type_raw if original_exp_type_raw in ("MONTHLY", "WEEKLY") else None

    start_time = str(payload.get("StartTime", "")).strip()
    stop_time = str(payload.get("StopTime", "")).strip()

    trading_enabled = str(payload.get("TRADINGENABLED", "TRUE")).strip().upper()
    trading_enabled = "TRUE" if trading_enabled == "TRUE" else "FALSE"

    # Find row by ORIGINAL (Symbol, ExpType, ExpieryDate) so editing expiry/type updates in place
    key_exp_type = original_exp_type if original_exp_type else exp_type
    key_mask = (
        (df["Symbol"].astype(str).str.strip() == key_symbol)
        & (df["ExpType"].astype(str).str.strip().str.upper() == key_exp_type)
        & (df["ExpieryDate"].astype(str).str.strip() == original_ex_date)
    )

    new_row = {
        "Symbol": symbol,
        "BaseSymbol": base_symbol,
        "Quantity": quantity,
        "StrikeRange": strike_range,
        "StrikeStep": strike_step,
        "PremiumUp": premium_up,
        "PremiumDown": premium_down,
        "Target": target,
        "StopLoss": stop_loss,
        "ExpieryDate": ex_date_out,
        "ExpType": exp_type,
        "StartTime": start_time,
        "StopTime": stop_time,
        "TRADINGENABLED": trading_enabled,
    }

    if key_mask.any():
        # Update existing row(s) column by column to avoid dtype issues
        for col, val in new_row.items():
            df.loc[key_mask, col] = val
        print(f"[UI] Updated existing setting for {symbol}, {exp_type}, {ex_date_out}")
    else:
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        print(f"[UI] Added new setting for {symbol}, {exp_type}, {ex_date_out}")

    try:
        df.to_csv("TradeSettings.csv", index=False)
    except Exception as e:
        print("[UI] Failed to write TradeSettings.csv in save_setting:", e)
        return jsonify({"error": "failed to write TradeSettings.csv"}), 500

    # When enabling trading for this row, clear its state so next entry uses fresh LTP/target/stop.
    if trading_enabled == "TRUE":
        state = load_state()
        _clear_state_for_key(state, f"{symbol}|{exp_type}|{ex_date_out}")
        save_state(state)

    return jsonify({"ok": True})


def _read_order_log_rows():
    """Read all rows from order_log.csv and return list of dicts (keys = column names)."""
    if not os.path.exists(ORDER_LOG_FILE):
        return []
    rows = []
    try:
        with open(ORDER_LOG_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                for row in reader:
                    # Older logs (before ce_request/pe_request columns were added) may have
                    # extra CSV columns with no header. csv.DictReader stores those under
                    # the special key None, which is not JSON-serializable when Flask
                    # tries to jsonify the list (it attempts to sort keys and hits
                    # None vs str). Drop that key to keep rows safe for JSON.
                    if None in row:
                        del row[None]
                    rows.append(row)
    except Exception as e:
        print("[ORDER_LOG] Failed to read order_log.csv:", e)
    return rows


def _parse_log_date(timestamp_str):
    """Parse timestamp from order_log (e.g. 2025-02-26T09:16:02) to date object."""
    if not timestamp_str or not isinstance(timestamp_str, str):
        return None
    try:
        part = timestamp_str.split("T")[0].strip()
        return datetime.strptime(part, "%Y-%m-%d").date()
    except Exception:
        return None


@app.route("/order-log")
def order_log_page():
    """Order Log page: shows all trading decisions from order_log.csv with time filter."""
    return render_template("order_log.html")


@app.route("/order-log-data", methods=["GET"])
def order_log_data():
    """
    Return order log entries as JSON. Query params:
    - filter: all | today | custom
    - start_date, end_date: YYYY-MM-DD (required when filter=custom)
    - base_symbol: optional, filter by base symbol name (e.g. NIFTY, BANKNIFTY)
    """
    filter_type = (request.args.get("filter") or "all").strip().lower()
    base_symbol_filter = (request.args.get("base_symbol") or "").strip().upper()
    rows = _read_order_log_rows()

    if base_symbol_filter:
        rows = [r for r in rows if (r.get("base_symbol") or "").strip().upper() == base_symbol_filter]

    if filter_type == "today":
        today = datetime.now().date()
        rows = [r for r in rows if _parse_log_date(r.get("timestamp")) == today]
    elif filter_type == "custom":
        start_str = request.args.get("start_date", "").strip()
        end_str = request.args.get("end_date", "").strip()
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
            end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
        except ValueError:
            start_date = end_date = None
        def in_range(r):
            d = _parse_log_date(r.get("timestamp"))
            if d is None:
                return False
            if start_date and end_date:
                return start_date <= d <= end_date
            if start_date:
                return d >= start_date
            if end_date:
                return d <= end_date
            return True

        if start_date or end_date:
            rows = [r for r in rows if in_range(r)]

    # Return in reverse chronological order (newest first)
    rows.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return jsonify(rows)


@app.route("/order-log-symbols", methods=["GET"])
def order_log_symbols():
    """Return distinct base_symbol values from order_log.csv for the symbol filter dropdown."""
    rows = _read_order_log_rows()
    symbols = sorted(set((r.get("base_symbol") or "").strip() for r in rows if (r.get("base_symbol") or "").strip()))
    return jsonify(symbols)


@app.route("/order-log-delete", methods=["POST"])
def order_log_delete():
    """Clear all order log entries (truncate order_log.csv to header only)."""
    try:
        with open(ORDER_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(ORDER_LOG_COLUMNS)
        print("[ORDER_LOG] Cleared all log entries.")
        return jsonify({"ok": True})
    except Exception as e:
        print("[ORDER_LOG] Failed to clear order log:", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/strategy")
def strategy_page():
    """
    Placeholder Strategy page for future controls/monitoring.
    """
    return render_template("strategy.html")


def run_strategy_loop():
    """
    Placeholder for the main strategy loop which was previously
    executed directly in the __main__ block.
    Not invoked yet; kept for future wiring from the Flask app.
    """
    credentials_dict_fyers = get_api_credentials_Fyers()
    redirect_uri = credentials_dict_fyers.get('redirect_uri')
    client_id = credentials_dict_fyers.get('client_id')
    secret_key = credentials_dict_fyers.get('secret_key')
    grant_type = credentials_dict_fyers.get('grant_type')
    response_type = credentials_dict_fyers.get('response_type')
    state = credentials_dict_fyers.get('state')
    TOTP_KEY = credentials_dict_fyers.get('totpkey')
    FY_ID = credentials_dict_fyers.get('FY_ID')
    PIN = credentials_dict_fyers.get('PIN')

    automated_login(
        client_id=client_id,
        redirect_uri=redirect_uri,
        secret_key=secret_key,
        FY_ID=FY_ID,
        PIN=PIN,
        TOTP_KEY=TOTP_KEY,
    )
    get_user_settings()

    # websocket connection
    fyres_websocket(FyerSymbolList)
    time.sleep(4)

    while True:
        now = datetime.now()
        print(f"\nStarting main strategy at {datetime.now()}")
        # main_strategy()
        time.sleep(1)


if __name__ == "__main__":
    # Bind to 0.0.0.0 so the app is reachable from other machines (e.g. http://217.217.251.11:5000 on VPS)
    app.run(host="0.0.0.0", port=3000, debug=True)
