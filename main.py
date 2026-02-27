import pandas as pd
import datetime  # full module
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
                fyers_symbol = None
                if pd.notna(ExpieryDate):
                    expiry_str = str(ExpieryDate).strip()
                    if ExpType == "MONTHLY":
                        # e.g., '29-05-2025' -> '25MAY'
                        expiry_date = datetime.strptime(expiry_str, '%d-%m-%Y')
                        new_date_string = expiry_date.strftime('%y%b').upper()
                        fyers_symbol = f"NSE:{BaseSymbol}{new_date_string}{Strike}{OptionType}"
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
            if exp_type != "MONTHLY":
                print(f"[STRATEGY] Skipping {symbol}: ExpType {exp_type} not yet implemented for options.")
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
                new_date_string = expiry_date.strftime("%y%b").upper()
            except Exception as e:
                print(f"[STRATEGY] Failed to parse expiry {expiry_str} for {symbol}: {e}")
                continue

            for strike in strikes:
                strike_int = int(strike)
                for opt_type in ("CE", "PE"):
                    fyers_symbol = f"NSE:{base_symbol}{new_date_string}{strike_int}{opt_type}"
                    option_symbols.append(fyers_symbol)

            option_key_by_symbol[base_symbol] = option_symbols
            FyerSymbolList.extend(option_symbols)
            print(f"[STRATEGY] Built {len(option_symbols)} option symbols for {symbol}")

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
    global strategy_running, FyerSymbolList
    while strategy_running:
        now_ts = datetime.now()
        snapshot_count = len(FyerSymbolList)
        print(f"[STRATEGY TICK] {now_ts} | tracking {snapshot_count} option symbols.")
        time.sleep(1)


@app.route("/strategy-status", methods=["GET"])
def strategy_status():
    """
    Return whether strategy is currently running, plus symbol count.
    """
    return jsonify({"running": strategy_running, "symbols": len(FyerSymbolList)})


@app.route("/start-strategy", methods=["POST"])
def start_strategy():
    """
    Start strategy:
      - login to Fyers
      - build option symbol lists from TradeSettings
      - start websocket subscription
      - start background strategy loop
    """
    global strategy_running

    if strategy_running:
        return jsonify({"ok": True, "message": "Strategy already running"})

    creds = get_api_credentials_Fyers()
    redirect_uri = creds.get('redirect_uri')
    client_id = creds.get('client_id')
    secret_key = creds.get('secret_key')
    TOTP_KEY = creds.get('totpkey')
    FY_ID = creds.get('FY_ID')
    PIN = creds.get('PIN')

    automated_login(
        client_id=client_id,
        redirect_uri=redirect_uri,
        secret_key=secret_key,
        FY_ID=FY_ID,
        PIN=PIN,
        TOTP_KEY=TOTP_KEY,
    )

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
    Exit All button endpoint.

    For now this just serves as a UI stub; the actual
    position-closing logic will be wired in later.
    """
    payload = {}
    try:
        payload = request.get_json(silent=True) or {}
    except Exception:
        payload = {}

    symbol = payload.get("symbol") or request.args.get("symbol")
    print(f"[UI] Exit All requested for symbol: {symbol} (logic not implemented yet).")
    return ("", 204)


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

    start_time = str(payload.get("StartTime", "")).strip()
    stop_time = str(payload.get("StopTime", "")).strip()

    trading_enabled = str(payload.get("TRADINGENABLED", "TRUE")).strip().upper()
    trading_enabled = "TRUE" if trading_enabled == "TRUE" else "FALSE"

    key_mask = (
        (df["Symbol"].astype(str).str.strip() == key_symbol)
        & (df["ExpType"].astype(str).str.strip().str.upper() == exp_type)
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

    return jsonify({"ok": True})


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
    # For now we only run the Flask UI. The trading strategy
    # loop remains available in run_strategy_loop() for later use.
    app.run(debug=True)
