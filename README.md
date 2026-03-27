# Kapil Spread Algo

Flask-based options strategy engine + web UI for Fyers.

This app:
- Logs in to Fyers
- Builds option chains around ATM for configured symbols
- Subscribes those symbols on websocket
- Runs a 1-second strategy loop for entry/exit management
- Logs events into `order_log.csv`
- Tracks open positions in `state.json`

---

## 1) Prerequisites

- Python 3.9+
- Valid Fyers account + API app
- Internet access for Fyers login/websocket

Recommended:
- Virtual environment (`.venv`)

---

## 2) Setup

### Option A: Quick start (recommended on Windows)

Run:

```bat
run.bat
```

`run.bat` will:
- install dependencies from `requirements.txt`
- start Flask app on port `3000`
- open browser at `http://127.0.0.1:3000`

### Option B: Manual start

```powershell
cd "D:\Desktop\python projects\Kapil Spread Algo"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open:

`http://127.0.0.1:3000`

---

## 3) Required Files

### `FyersCredentials.csv`

Create in project root with:

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

### `TradeSettings.csv`

Required columns:

```text
Symbol,BaseSymbol,Quantity,StrikeRange,StrikeStep,PremiumUp,PremiumDown,Target,StopLoss,ExpieryDate,ExpType,StartTime,StopTime,TRADINGENABLED
```

Example:

```text
Symbol,BaseSymbol,Quantity,StrikeRange,StrikeStep,PremiumUp,PremiumDown,Target,StopLoss,ExpieryDate,ExpType,StartTime,StopTime,TRADINGENABLED
NSE:NIFTY26MARFUT,NIFTY,65,10,50,210,200,3,,24-03-2026,WEEKLY,09:15,15:15,TRUE
```

Field notes:
- `Symbol`: full underlying (example `NSE:NIFTY26MARFUT`)
- `BaseSymbol`: option base name (example `NIFTY`)
- `StrikeRange`: strikes up/down from ATM
- `StrikeStep`: strike increment (NIFTY typically 50)
- `ExpType`: `WEEKLY` or `MONTHLY`
- `ExpieryDate`: `DD-MM-YYYY`
- `TRADINGENABLED`: `TRUE` or `FALSE`

---

## 4) Important Current Rules

### Single row per symbol

The app now enforces **one setting row per symbol**.

That means:
- `NSE:NIFTY26MARFUT` cannot exist as both weekly and monthly in two rows at the same time.
- Saving the same symbol again updates the existing row.
- Duplicate symbol rows are auto-cleaned by the backend.

### Strike parsing fix

`StrikeRange` and `StrikeStep` now parse robustly from values like:
- `10`
- `10.0`
- numeric CSV values

This prevents false logs like:
- `invalid StrikeRange/StrikeStep (0, 50)`

and ensures websocket subscriptions are generated when data is valid.

---

## 5) Strategy Flow

When you click **Start Strategy**:

1. Fyers login is performed
2. Option symbols are generated from `TradeSettings.csv`
3. Websocket subscribes to generated option list
4. Background strategy loop starts (tick every ~1 second)

Entry logic (per enabled row):
- Scans live option LTPs
- Picks CE and PE within premium range (`PremiumDown` to `PremiumUp`)
- Places entry orders

Exit logic:
- Target hit -> `EXIT_TARGET`
- Stop-loss hit -> `EXIT_STOPLOSS`
- Stop time hit -> `EXIT_STOPTIME`
- Manual exit -> `MANUAL_EXIT`

All events are written to `order_log.csv`.

---

## 6) Order Repricing Behavior

For open/pending orders, bot reprices automatically:
- BUY side -> latest ASK
- SELL side -> latest BID

Current timing:
- status/reprice poll interval: `1` second
- failed modify retry gap: `0.5` second (up to 3 attempts)

Requests are synchronous in loop (waits for response before next call).

---

## 7) Key Endpoints

- `GET /` -> Symbol Settings UI
- `POST /start-strategy` -> Start login + websocket + strategy loop
- `POST /stop-strategy` -> Stop strategy + request websocket close
- `GET /strategy-status` -> Running status
- `GET /strategy-positions` -> Open strategy positions from `state.json`
- `POST /exit-all` -> Exit all open strategy positions
- `GET /order-log` -> Order log page
- `GET /order-log-data` -> Order log JSON

---

## 8) Troubleshooting

### Strategy starts but tracks 0 symbols

Check:
- `TRADINGENABLED` is `TRUE`
- `StrikeRange > 0`
- `StrikeStep > 0`
- valid `ExpieryDate` format (`DD-MM-YYYY`)
- valid `Symbol`/`BaseSymbol`
- successful Fyers login

### Duplicate symbol rows in settings

Backend auto-cleans duplicates now.  
Still, keep one row per symbol in imported CSV.

### No entries happening

Possible reasons:
- outside `StartTime`/`StopTime`
- no CE/PE in configured premium band
- no websocket LTP updates

Check `order_log.csv` and console logs.

---

## 9) Safety Note

Use small qty for live testing.  
Validate risk, lot size, and broker behavior before scaling.

