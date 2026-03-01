# Strategy Flow – Step-by-Step

This document describes how the Kapil Spread Algo strategy works from start to finish: how it selects options, takes trades, hits target/stop, how the Exit button and `state.json` work, and what gets written to the order log.

---

## 1. Starting the Strategy

1. **Start Strategy** (UI or `POST /start-strategy`)
   - Reads **FyersCredentials.csv** and logs into Fyers.
   - Reads **TradeSettings.csv** and, for each row with `TRADINGENABLED = TRUE`:
     - Fetches LTP of the underlying (e.g. `NSE:NIFTY26MARFUT`).
     - Rounds LTP to nearest **StrikeStep** to get ATM strike.
     - Builds strikes from **ATM − (StrikeRange × StrikeStep)** to **ATM + (StrikeRange × StrikeStep)**.
     - For each strike, creates CE and PE symbols: `NSE:{BaseSymbol}{YYMMM}{Strike}{CE|PE}` (e.g. `NSE:NIFTY26MAR25000CE`).
     - Stores the list in **option_key_by_symbol[BaseSymbol]** and adds all to **FyerSymbolList**.
   - Starts the **Fyers websocket** in a background thread (subscribes to all option symbols in `FyerSymbolList`).
   - Starts the **strategy loop** (`_strategy_loop_worker`) in another background thread.

2. **Strategy loop** runs every ~1 second:
   - Reads **TradeSettings.csv** and **state.json**.
   - For each row with `TRADINGENABLED = TRUE` and current time inside **StartTime–StopTime**, it either:
     - **Enters** a new trade (if not in position), or
     - **Monitors** an open trade for target/stop/stop-time, and applies Target/StopLoss edits from the CSV.

---

## 2. How Options Are Selected and a Trade Is Taken

- **Time window:** Entry is only attempted when **StartTime ≤ current time ≤ StopTime** (e.g. 09:15–15:30).

- **Premium filter:** For the row’s **BaseSymbol** (e.g. NIFTY, BANKNIFTY), the strategy takes all option symbols from **option_key_by_symbol[BaseSymbol]** and their **latest LTP** from the websocket (`FyresIntegration.shared_data`). It keeps only options whose LTP is within **[PremiumDown, PremiumUp]**.

- **Strike selection (within your strike range):**  
  Only options built from **your strike range** (ATM ± StrikeRange × StrikeStep) are considered. Among those:
  - For **CE**: it keeps only contracts whose LTP is in **[PremiumDown, PremiumUp]**, then picks the one with **lowest LTP** → that is the **call strike** (e.g. `NSE:NIFTY26MAR25000CE`).
  - For **PE**: same premium filter, then **lowest LTP** among PE → that is the **put strike** (e.g. `NSE:NIFTY26MAR25000PE`).  
  So: **lowest LTP for the call symbol, and lowest LTP for the put symbol, both within the strike range you provided** (and within the premium band).

- **Entry (virtual/live later):**
  - **Entry combined price** = Call LTP + Put LTP.
  - **Target (absolute)** = entry_combined × (Target% / 100).
  - **Stop (absolute)** = entry_combined × (StopLoss% / 100).
  - Strategy records this as an **ENTRY** in **state.json** and writes an **ENTRY** row to **order_log.csv** (see sample below). Real BUY orders can be placed at the same point (currently TODO).

- **State key:** Each “strategy row” is uniquely identified by **strategy_key** = `Symbol|ExpType|ExpieryDate` (e.g. `NSE:NIFTY26MARFUT|MONTHLY|29-05-2025`). This key is used in **state.json** and in order logs.

---

## 3. Target and Stop-Loss – How Exits Work

- **Target exit:** Every tick, for an open position, the strategy computes **combined LTP = CE_LTP + PE_LTP**. If **combined ≥ entry_combined + target_abs** (and target_abs > 0), it:
  - Logs **EXIT_TARGET** to **order_log.csv**.
  - Sets **in_position = False** in **state.json** for that key.
  - Sets **TRADINGENABLED = FALSE** for that row in **TradeSettings.csv**.

- **Stop-loss exit:** If **combined ≤ entry_combined − stop_abs** (and stop_abs > 0), it:
  - Logs **EXIT_STOPLOSS** to **order_log.csv**.
  - Same state and CSV updates as target.

- **Stop-time exit:** If **current time ≥ StopTime** and the strategy still has an open position for that key, it:
  - Logs **EXIT_STOPTIME** to **order_log.csv**.
  - Closes the position in state and sets **TRADINGENABLED = FALSE**.

- **Editing Target/StopLoss while trade is open:**  
  If you change **Target** or **StopLoss** in **TradeSettings.csv** (or via UI) while the trade is open, the strategy loop **detects the change** on the next tick, **recomputes target_abs and stop_abs** from the new percentages (based on **entry_combined**), **updates state.json** with the new values, and writes a **TARGET_STOPLOSS_UPDATED** row to **order_log.csv** with old vs new target% and stop%.

---

## 4. Exit Button

- **Exit All** is exposed as `POST /exit-all`. You can pass an optional **symbol** (e.g. the full Symbol from TradeSettings) to exit only that symbol’s strategy position(s), or omit to exit all.

- **Intended behaviour (when fully wired):**
  - For the selected symbol(s), the backend should:
    - Find all **state.json** entries that match (e.g. same Symbol/BaseSymbol) and have **in_position = True**.
    - For each, get current LTP of CE and PE, then:
      - Write an **order log** row with event like **EXIT_BUTTON** and details such as: *“Exiting trade for strike prices &lt;CE&gt; &lt;PE&gt; at price &lt;combined&gt;”*.
      - Set **in_position = False** in **state.json** and **TRADINGENABLED = FALSE** in **TradeSettings.csv** for the corresponding row.
  - Optionally place real square-off (SELL) orders for those CE/PE.

- **Current status:** The route exists and accepts `symbol`; the actual state update and order-log write for Exit can be wired so that pressing Exit logs exactly: *“Exiting trade &lt;symbol&gt; for strike prices &lt;call_symbol&gt;, &lt;put_symbol&gt; at price &lt;price&gt;”* in **order_log.csv**.

---

## 5. How state.json Works

- **File:** `state.json` in the project root.

- **Purpose:** Persist, per strategy row, whether we are in a position and which strikes we bought at what levels. The strategy loop **reads** it at the start of each tick and **writes** it back after processing (so it survives restarts).

- **Keys:** Each key is **strategy_key** = `Symbol|ExpType|ExpieryDate` (e.g. `NSE:NIFTY26MARFUT|MONTHLY|29-05-2025`).

- **Value (record) for each key:**
  - **in_position:** `true` = open position, `false` = no position (or closed).
  - **symbol:** Full symbol from TradeSettings (e.g. `NSE:NIFTY26MARFUT`).
  - **base_symbol:** e.g. `NIFTY`.
  - **call_symbol:** Finalized CE contract (e.g. `NSE:NIFTY26MAR25000CE`).
  - **put_symbol:** Finalized PE contract (e.g. `NSE:NIFTY26MAR25000PE`).
  - **entry_call:** Entry LTP of the call.
  - **entry_put:** Entry LTP of the put.
  - **entry_combined:** entry_call + entry_put.
  - **target_pct,** **stop_pct:** Target and stop-loss percentages.
  - **target_abs,** **stop_abs:** Absolute target and stop amounts (used for exit checks).

**Example state.json (one open position):**

```json
{
  "NSE:NIFTY26MARFUT|MONTHLY|29-05-2025": {
    "in_position": true,
    "symbol": "NSE:NIFTY26MARFUT",
    "base_symbol": "NIFTY",
    "call_symbol": "NSE:NIFTY26MAR25000CE",
    "put_symbol": "NSE:NIFTY26MAR25000PE",
    "entry_call": 135.5,
    "entry_put": 128.0,
    "entry_combined": 263.5,
    "target_pct": 10,
    "stop_pct": 5,
    "target_abs": 26.35,
    "stop_abs": 13.175
  }
}
```

After exit (target/stop/stop-time/exit button), that key’s **in_position** is set to **false** (other fields may remain for history). The **Positions** tab in the Strategy page shows only entries where **in_position** is true.

---

## 6. Order Log (order_log.csv) – Format and Sample Rows

- **File:** `order_log.csv` (comma-separated, UTF-8).

- **Columns:**  
  `timestamp`, `event`, `strategy_key`, `base_symbol`, `symbol`, `call_symbol`, `put_symbol`, `price_call`, `price_put`, `combined_price`, `target_pct`, `stop_pct`, `target_abs`, `stop_abs`, `details`

- **Events:**  
  - **ENTRY** – Finalized strikes and virtual buy (call + put), with entry prices and target/stop.  
  - **TARGET_STOPLOSS_UPDATED** – Target/StopLoss edited while trade was open; new target%, stop%, and absolute values.  
  - **EXIT_TARGET** – Exited because combined price reached target.  
  - **EXIT_STOPLOSS** – Exited because combined price hit stop-loss.  
  - **EXIT_STOPTIME** – Exited at stop time.  
  - **EXIT_BUTTON** – (When wired) User pressed Exit; details describe exiting for those strike prices at that price.

**Sample order log rows (tabular):**

```csv
timestamp,event,strategy_key,base_symbol,symbol,call_symbol,put_symbol,price_call,price_put,combined_price,target_pct,stop_pct,target_abs,stop_abs,details
2025-02-26T09:16:02,ENTRY,NSE:NIFTY26MARFUT|MONTHLY|29-05-2025,NIFTY,NSE:NIFTY26MARFUT,NSE:NIFTY26MAR25000CE,NSE:NIFTY26MAR25000PE,135.5,128.0,263.5,10,5,26.35,13.175,"Finalized entry strikes and virtual buy for long straddle."
2025-02-26T10:30:15,TARGET_STOPLOSS_UPDATED,NSE:NIFTY26MARFUT|MONTHLY|29-05-2025,NIFTY,NSE:NIFTY26MARFUT,NSE:NIFTY26MAR25000CE,NSE:NIFTY26MAR25000PE,142.0,131.0,273.0,15,7,39.525,18.445,"Targets updated while trade open. Old target=10%, new target=15%, old stop=5%, new stop=7%."
2025-02-26T11:00:00,EXIT_TARGET,NSE:NIFTY26MARFUT|MONTHLY|29-05-2025,NIFTY,NSE:NIFTY26MARFUT,NSE:NIFTY26MAR25000CE,NSE:NIFTY26MAR25000PE,155.2,135.1,290.3,15,7,39.525,18.445,"Exiting trade on target hit."
```

Another example for stop-time and (conceptual) exit button:

```csv
2025-02-26T15:30:01,EXIT_STOPTIME,NSE:BANKNIFTY26MARFUT|MONTHLY|26-03-2026,BANKNIFTY,NSE:BANKNIFTY26MARFUT,NSE:BANKNIFTY26MAR52000CE,NSE:BANKNIFTY26MAR52000PE,,,,,,,"Stop-time exit at 15:30:01 for window 09:15-15:30"
2025-02-26T14:22:00,EXIT_BUTTON,NSE:NIFTY26MARFUT|MONTHLY|29-05-2025,NIFTY,NSE:NIFTY26MARFUT,NSE:NIFTY26MAR25000CE,NSE:NIFTY26MAR25000PE,148.0,132.0,280.0,10,5,26.35,13.175,"Exiting trade NIFTY for strike prices NSE:NIFTY26MAR25000CE, NSE:NIFTY26MAR25000PE at price 280.0"
```

You can open **order_log.csv** in Excel or use the **Order Log** page in the web UI (with filters: all / today / custom date range) to view these events in a table.

---

## Summary Flow (One Symbol)

1. **Start Strategy** → Login → Build option list from TradeSettings (ATM ± StrikeRange) → Subscribe websocket → Start loop.  
2. **At StartTime** → For each enabled row, if not in position: get LTPs, filter by PremiumDown–PremiumUp, choose lowest-premium CE and lowest-premium PE → **ENTRY** (state + order_log).  
3. **While in position** → Each tick: (optional) apply Target/StopLoss changes from CSV and log **TARGET_STOPLOSS_UPDATED**; then check combined LTP vs target_abs/stop_abs and **EXIT_TARGET** or **EXIT_STOPLOSS** if hit; at **StopTime** → **EXIT_STOPTIME**.  
4. **Exit button** → (When wired) Close position for chosen symbol(s), update state and CSV, write **EXIT_BUTTON** with “Exiting trade … for strike prices … at price …”.  
5. **state.json** holds per-strategy_key position and strike/price data; **order_log.csv** holds every event in tabular form for audit and the Order Log UI.

---

## Clarifications

- **No position open yet – you change Target from 100 to 50:**  
  When the strategy opens a **new** position, it reads **Target** and **StopLoss** from the **current** row in TradeSettings.csv at that moment. So if you set Target to 50 (and save/CSV is updated) before any position is opened for that symbol, the position that opens will use **Target = 50** (and the corresponding target_abs from entry_combined × 50%).

- **Stop Strategy, add a new symbol (e.g. NIFTY), then Start Strategy:**  
  - **All enabled symbols run:** Start Strategy reads TradeSettings again and builds option lists for **every** row with `TRADINGENABLED = TRUE`, including the newly added NIFTY. So all three (or however many you have) will be running.  
  - **Previous positions are remembered:** `state.json` is stored on disk and is **not** cleared when you stop the strategy. When you click Start Strategy, the strategy loop loads `state.json` on every tick. So if before stopping you had an open position in NIFTY (or any symbol), that key will still be in state.json with `in_position: true`. The strategy will **load that first** and continue to **monitor** that position (target/stop/stop-time); it will **not** open a second position for the same key.
