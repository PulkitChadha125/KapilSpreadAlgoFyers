Kapil Spread Algo
==================

This project is a Flask-based UI and trading engine for option strategies on the Fyers platform.  
The web UI lets you configure per-symbol settings in a CSV file and then start a background strategy that:

- Logs into Fyers using credentials from `FyersCredentials.csv`
- Builds option contracts (CE/PE) around the ATM based on your settings
- Subscribes those contracts to the Fyers websocket
- Runs a per-second strategy loop that:
  - Automatically picks CE/PE strikes inside your configured premium band
  - Places paired CE/PE entry orders
  - Tracks open positions in `state.json`
  - Manages target, stop-loss, manual exit and stop-time exits
  - Logs every decision into `order_log.csv` and the Order Log UI

Project Structure
-----------------

- `main.py`  
  - Flask app & routes  
  - Strategy bootstrap (`/start-strategy`, `/stop-strategy`, `/strategy-status`)  
  - REST API for:
    - Reading/writing `TradeSettings.csv` (including `Target`, `StopLoss`, Start/Stop time, enable flag)
    - Toggling trading, deleting/importing/exporting settings
    - Viewing/clearing the Order Log
    - Triggering Exit All for open positions
  - Building option symbols (`build_option_subscriptions`) and global list `FyerSymbolList` for websocket
  - Main strategy loop (`_strategy_loop_worker`) that:
    - Reads `TradeSettings.csv` every second
    - Loads open positions from `state.json`
    - Enters trades when CE/PE LTPs fall inside the configured premium range
    - Tracks each position with entry prices, combined premium, target/stop in `state.json`
    - Recomputes target/stop if you change them in the UI while a trade is open
    - Exits on:
      - Target hit (`EXIT_TARGET`)
      - Stop-loss hit (`EXIT_STOPLOSS`)
      - Stop time (`EXIT_STOPTIME`)
      - Manual exit (`MANUAL_EXIT` via the Exit button)
    - Disables trading for a row after the position is fully closed (sets `TRADINGENABLED=FALSE`)
    - Writes every event into `order_log.csv` via `append_order_log(...)`

- `FyresIntegration.py`  
  - Fyers login (`automated_login`)  
  - `get_ltp` helper  
  - Websocket subscription helpers (`fyres_websocket`, etc.)  
  - Shared dicts (`shared_data`, `shared_data_2`) where latest LTPs are stored

- `templates/symbol_settings.html`  
  - Main web UI for viewing/editing symbol settings  
  - Edit/Add modal, delete button, trading toggle, import/export buttons  
  - Strategy Start/Stop buttons and a live **Strategy: Running/Stopped** badge

- `templates/order_log.html`  
  - Order Log UI (`/order-log`) that reads from `order_log.csv` via `/order-log-data`
  - Filters by base symbol and time range (All / Today / Custom range)
  - Shows all strategy events:
    - `ENTRY`
    - `TARGET_STOPLOSS_UPDATED` (when you change Target/StopLoss while a trade is open)
    - `EXIT_TARGET`, `EXIT_STOPLOSS`, `EXIT_STOPTIME`, `MANUAL_EXIT`
  - Columns:
    - CE/PE option symbols used
    - Entry/exit prices and combined premium
    - Target % / Stop %
    - PnL (points), PnL % and PnL Amount (all rounded to 2 decimals, green for profit and red for loss)
    - Net PnL badge at the top aggregating PnL Amount over all visible rows
    - Details column with raw Fyers API messages
  - Click on any ENTRY / EXIT row to open a modal with the full CE/PE order request/response JSON

- `state.json`  
  - JSON snapshot of **open positions only**
  - Keys are `Symbol|ExpType|ExpieryDate` (e.g. `NSE:NIFTY26MARFUT|WEEKLY|10-03-2026`)
  - Each record stores:
    - `symbol`, `base_symbol`
    - `call_symbol`, `put_symbol`
    - `entry_call`, `entry_put`, `entry_combined`
    - `target_pct`, `stop_pct`, `target_abs`, `stop_abs`
    - `quantity`
    - `in_position` flag
  - On any full exit (target, stop-loss, stop-time, manual exit) the corresponding key is removed
  - When you re-enable trading for a symbol, the next entry starts from fresh LTP and writes a new record

- `order_log.csv`  
  - Tabular log written by `append_order_log(...)`
  - Columns include:
    - Timestamp (IST), event type, base symbol, option symbols
    - Entry/exit prices and combined premium
    - Target/stop in % and absolute points
    - Realised PnL (points, %, and amount per trade)
    - Details string and raw CE/PE request/response payloads (JSON-encoded)

- `TradeSettings.csv`  
  - Primary configuration source for symbol settings (see format below)

- `requirements.txt`  
  - Python dependencies for the project

Prerequisites
-------------

- Python 3.9+ (recommended)
- A Fyers API app and valid credentials
- A virtual environment (recommended)

Setup
-----

1. **Create and activate virtual environment (PowerShell example):**

   ```powershell
   cd "D:\Desktop\python projects\Kapil Spread Algo"
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Fyers credentials**

   Create `FyersCredentials.csv` in the project root (if not already present) with at least:

   ```text
   Title,Value
   client_id,YOUR_APP_ID-100
   secret_key,YOUR_SECRET
   redirect_uri,https://your-redirect-url
   totpkey,BASE32_TOTP_KEY
   FY_ID,YOUR_FYERS_ID
   PIN,YOUR_PIN
   grant_type,authorization_code
   response_type,code
   state,None
   ```

   These are read by `get_api_credentials_Fyers()` in `main.py`.

4. **Configure Trade Settings**

   `TradeSettings.csv` must have the following columns:

   ```text
   Symbol,BaseSymbol,Quantity,StrikeRange,StrikeStep,PremiumUp,PremiumDown,Target,StopLoss,ExpieryDate,ExpType,StartTime,StopTime,TRADINGENABLED
   ```

   Example:

   ```text
   Symbol,BaseSymbol,Quantity,StrikeRange,StrikeStep,PremiumUp,PremiumDown,Target,StopLoss,ExpieryDate,ExpType,StartTime,StopTime,TRADINGENABLED
   NSE:NIFTY26MARFUT,NIFTY,1,10,50,140,130,10,10,29-05-2025,MONTHLY,09:15,15:30,TRUE
   NSE:BANKNIFTY26MARFUT,BANKNIFTY,65,10,100,140,100,0,0,26-03-2026,MONTHLY,09:15,15:15,TRUE
   ```

   - `Symbol`: full Fyers underlying (used for LTP/login checks), e.g. `NSE:NIFTY26MARFUT`
   - `BaseSymbol`: option base (used to format contracts), e.g. `NIFTY`
   - `StrikeRange`: number of steps up/down from ATM (e.g. 10 → 10 up + 10 down)
   - `StrikeStep`: step size in points (e.g. 50)
   - `ExpType`: currently `MONTHLY` is implemented for options
   - `TRADINGENABLED`: `TRUE` or `FALSE`

Running the App
---------------

1. **Start the Flask server:**

   ```powershell
   .venv\Scripts\activate
   python main.py
   ```

2. **Open the UI:**

   - Visit `http://127.0.0.1:5000/` in your browser.

3. **Symbol Settings UI**

   - View all rows from `TradeSettings.csv`.
   - Use the **Edit** button (pencil) to adjust:
     - `Symbol`, `Base Symbol`, `Quantity`, `StrikeRange`, `StrikeStep`
     - `PremiumUp`, `PremiumDown`, `Target`, `StopLoss`
     - `ExpType` (MONTHLY/WEEKLY), `ExpieryDate` (date picker), `StartTime`, `StopTime`
     - `TRADINGENABLED`
   - Use the **trash icon** to delete a setting (row removed from CSV, does **not** square off positions).
   - Use the **yellow exit icon** to **Square Off Positions** for that setting (currently a stub, logs to console).
   - Use **Add New Setting** to insert a new row into `TradeSettings.csv`.
   - Use **Import Settings**/**Export Settings** to manage the CSV via the UI.

Strategy Bootstrap
------------------

The strategy is started and stopped from the navbar buttons and runs as two background threads:

- **Start Strategy**

  - Route: `POST /start-strategy`
  - Steps:
    1. Logs into Fyers using `FyersCredentials.csv`
    2. Reads `TradeSettings.csv`
    3. For each row with `TRADINGENABLED == TRUE`:
       - Normalizes the underlying symbol for LTP
       - Fetches LTP
       - Rounds to nearest `StrikeStep` to get ATM
       - Builds strikes from `-StrikeRange` to `+StrikeRange`
       - Formats monthly/weekly option contracts for both CE and PE using:
         `NSE:{BaseSymbol}{ExpiryCode}{Strike}{CE/PE}`
       - Stores them under `option_key_by_symbol[unique_key]`
       - Adds them to `FyerSymbolList`
    4. Starts the Fyers websocket via `fyres_websocket(FyerSymbolList)` in a background thread
    5. Starts `_strategy_loop_worker()` in another background thread, which:
       - Once per second:
         - Reloads `TradeSettings.csv`
         - Reloads `state.json` (open positions only)
         - For each enabled row:
           - Forces an exit if current time is past StopTime (`EXIT_STOPTIME`)
           - If not in a position yet:
             - Scans all subscribed options for that row
             - Chooses the cheapest CE and PE whose LTP is inside the `[PremiumDown, PremiumUp]` range
             - Places paired BUY orders and logs an `ENTRY`
             - Stores the entry snapshot in `state.json`
           - If already in a position:
             - Monitors combined CE+PE LTP for target / stop-loss hits
             - Detects live changes to Target/StopLoss in `TradeSettings.csv` and logs `TARGET_STOPLOSS_UPDATED`
             - On target/stop/stop-time/manual exit:
               - Places SELL orders
               - Computes PnL
               - Logs the appropriate `EXIT_*` event
               - Clears that key from `state.json`
               - Sets `TRADINGENABLED=FALSE` so next enable starts fresh

- **Stop Strategy**

  - Route: `POST /stop-strategy`
  - Sets a global flag `strategy_running = False` to stop the tick loop.

- **Status Indicator**

  - The UI calls `GET /strategy-status` and shows a badge:
    - **Strategy: Running** (green) when `running == true`
    - **Strategy: Stopped** (grey) otherwise

Strategy Logic Overview
-----------------------

The current code implements a complete CE+PE “spread” strategy loop:

- **Entry logic**
  - For each enabled row in `TradeSettings.csv` and within `[StartTime, StopTime]`:
    - Use the option list generated by `build_option_subscriptions(...)`
    - For each option, read latest LTP from `FyresIntegration.shared_data`
    - Keep the cheapest CE and PE whose LTP lies in `[PremiumDown, PremiumUp]`
    - When both sides are available:
      - Compute `entry_combined = entry_call + entry_put`
      - Compute `target_abs = entry_combined * Target%`
      - Compute `stop_abs   = entry_combined * StopLoss%`
      - Place CE/PE BUY orders via `place_order(...)`
      - Log an `ENTRY` event to `order_log.csv`
      - Save the full entry snapshot to `state.json`

- **Live target/stop updates**
  - While a trade is open, any manual edits you make to `Target`/`StopLoss` in the UI:
    - Are detected on the next tick
    - Recalculate `target_abs` / `stop_abs` from the original `entry_combined`
    - Log a `TARGET_STOPLOSS_UPDATED` event (anchored to the entry prices)

- **Exit logic**
  - On each tick, for open positions:
    - Read current CE/PE LTPs from `shared_data`
    - Compute `combined = price_ce + price_pe`
    - If `combined >= entry_combined + target_abs` → `EXIT_TARGET`
    - Else if `combined <= entry_combined - stop_abs` → `EXIT_STOPLOSS`
    - Independently, if current time >= `StopTime` → `EXIT_STOPTIME`
    - Manual “Exit All” from the UI uses the latest LTPs and logs `MANUAL_EXIT`
  - Every exit:
    - Places SELL orders with the current LTP as limit
    - Logs prices, target/stop and realised PnL to `order_log.csv`
    - Removes the key from `state.json`
    - Sets `TRADINGENABLED=FALSE` so next enable starts fresh

Security & Safety
-----------------

- This code is intended for **development and paper/very small live testing**, not for immediate production deployment.
- Always validate:
  - Position sizing
  - Order types
  - Exchange-specific constraints
- Add robust logging, error handling, and risk checks before enabling real capital.

License
-------

This project is private to you; no license is included. Use and modify it as you see fit for your own trading workflow.

