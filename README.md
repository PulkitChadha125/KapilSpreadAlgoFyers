Kapil Spread Algo
==================

This project is a Flask-based UI and trading harness for option strategies on the Fyers platform.  
The web UI lets you configure per-symbol settings in a CSV file and then start a background strategy that:

- Logs into Fyers using credentials from `FyersCredentials.csv`
- Builds option contracts (CE/PE) around the ATM based on your settings
- Subscribes those contracts to the Fyers websocket
- Runs a per-second strategy loop (ready for your trading logic)

> NOTE: The current strategy loop only builds subscriptions and logs ticks.  
> Actual trade entry/exit logic is intentionally left to be implemented next.

Project Structure
-----------------

- `main.py`  
  - Flask app & routes  
  - Strategy bootstrap (`/start-strategy`, `/stop-strategy`, `/strategy-status`)  
  - Reading/writing `TradeSettings.csv` (including `Target` and `StopLoss`)  
  - Building option symbols and parent list `FyerSymbolList` for websocket

- `FyresIntegration.py`  
  - Fyers login (`automated_login`)  
  - `get_ltp` helper  
  - Websocket subscription helpers (`fyres_websocket`, etc.)  
  - Shared dicts (`shared_data`, `shared_data_2`) where latest LTPs are stored

- `templates/symbol_settings.html`  
  - Main web UI for viewing/editing symbol settings  
  - Edit/Add modal, delete button, square-off button, trading toggle, import/export buttons  
  - Strategy Start/Stop buttons and a live **Strategy: Running/Stopped** badge

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

The strategy is started and stopped from the navbar buttons:

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
       - Formats monthly option contracts for both CE and PE using:
         `NSE:{BaseSymbol}{YYMMM}{Strike}{CE/PE}`
       - Stores them under `option_key_by_symbol[BaseSymbol]`
       - Adds them to `FyerSymbolList`
    4. Starts the Fyers websocket via `fyres_websocket(FyerSymbolList)` in a background thread
    5. Starts `_strategy_loop_worker()` in another background thread

  - The loop currently logs:
    ```text
    [STRATEGY TICK] <timestamp> | tracking <N> option symbols.
    ```

- **Stop Strategy**

  - Route: `POST /stop-strategy`
  - Sets a global flag `strategy_running = False` to stop the tick loop.

- **Status Indicator**

  - The UI calls `GET /strategy-status` and shows a badge:
    - **Strategy: Running** (green) when `running == true`
    - **Strategy: Stopped** (grey) otherwise

Extending With Trading Logic
----------------------------

The next step is to plug actual trading logic into `_strategy_loop_worker()`, using the latest option LTPs from:

- `FyresIntegration.shared_data` for underlying quotes
- Option quotes via the subscribed websocket (`FyerSymbolList`)

Recommended approach:

1. In each tick, iterate your option lists in `option_key_by_symbol`.
2. For each option symbol, read its latest LTP from the shared data store.
3. Evaluate entry/exit conditions based on `Target`, `StopLoss`, time filters (`StartTime`/`StopTime`), etc.
4. Place/cancel orders via Fyers REST APIs (integrate via `FyresIntegration.py`).

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

