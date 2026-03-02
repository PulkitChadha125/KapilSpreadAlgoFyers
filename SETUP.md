# Hosting Kapil Spread Algo on a Windows VPS (Remote Access)

This guide explains how to run the app on a **Windows VPS** so you can use it from anywhere via a URL. Once set up, open **`http://217.217.251.11:5000`** from any device (outside the VPS) to reach the **Symbol Settings** page.

---

## 1. Prerequisites

- A **Windows VPS** (e.g. Windows Server 2019/2022 or Windows 10/11) with RDP or remote access.
- **Administrator** access on the VPS (needed for firewall and optional service setup).
- Your project files (or this repo) copied to the VPS, e.g. `C:\KapilSpreadAlgo`.

---

## 2. Install Python on the VPS

1. Download the latest **Python 3.11 or 3.12** Windows installer from [python.org](https://www.python.org/downloads/).
2. Run the installer.
3. **Check “Add Python to PATH”** and choose “Install for all users” if available.
4. Complete the installation, then open a **new** Command Prompt or PowerShell.
5. Verify:
   ```powershell
   python --version
   pip --version
   ```

---

## 3. Install the App and Dependencies

1. Open **Command Prompt** or **PowerShell** and go to the project folder:
   ```powershell
   cd C:\KapilSpreadAlgo
   ```
   (Use the path where you copied the project.)

2. Create a virtual environment (recommended):
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Ensure your config files exist in the same folder:
   - `FyersCredentials.csv` (Fyers API credentials)
   - `TradeSettings.csv` (symbol settings)
   - `.env` is optional; create it if you use env vars.

---

## 4. Allow Remote Access (Bind to All Interfaces)

By default, Flask listens only on `127.0.0.1`, so it is not reachable from outside the VPS. You must run it so it listens on **all interfaces** (`0.0.0.0`).

**Option A – One-time run from command line**

```powershell
cd C:\KapilSpreadAlgo
venv\Scripts\activate
set FLASK_APP=main.py
set FLASK_RUN_HOST=0.0.0.0
set FLASK_RUN_PORT=5000
python main.py
```

Or run Python directly with host and port:

```powershell
python -c "from main import app; app.run(host='0.0.0.0', port=5000, debug=False)"
```

**Option B – Change the app so it always listens on 0.0.0.0**

Edit `main.py` and replace the last lines so they look like this:

```python
if __name__ == "__main__":
    # Listen on all interfaces so the app is reachable from other machines (e.g. VPS)
    app.run(host="0.0.0.0", port=5000, debug=False)
```

Then start the app with:

```powershell
python main.py
```

Use **port 5000** (or another port you choose) consistently for the next step.

---

## 5. Open the Port in Windows Firewall

You must allow inbound traffic on the port the app uses (e.g. **5000**) so that your browser can connect from outside.

### Method 1: Windows Defender Firewall (GUI)

1. On the VPS, press **Win + R**, type `wf.msc`, press Enter to open **Windows Defender Firewall with Advanced Security**.
2. In the left pane, click **Inbound Rules**.
3. In the right pane, click **New Rule…**.
4. Rule Type: select **Port** → Next.
5. TCP, **Specific local ports:** type `5000` (or the port you use) → Next.
6. Action: **Allow the connection** → Next.
7. Profile: leave **Domain**, **Private**, and **Public** all checked (or at least **Public** if the VPS is on a public network) → Next.
8. Name: e.g. **Kapil Spread Algo – Port 5000** → Finish.

### Method 2: PowerShell (Run as Administrator)

```powershell
New-NetFirewallRule -DisplayName "Kapil Spread Algo - Port 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

To use a different port (e.g. 8080), replace `5000` with that port in both the rule and when starting the app.

### Verify the rule

- In **wf.msc** → **Inbound Rules**, find **Kapil Spread Algo – Port 5000** and ensure it is **Enabled**.
- From your **local PC**, open a browser and go to `http://217.217.251.11:5000`. If the app is running and the firewall allows the port, the Symbol Settings page should load.

### Contabo VPS – open port 5000 in Contabo’s firewall

**If you use Contabo**, they have their **own firewall** in the control panel. You must allow port **5000** there as well, or `http://217.217.251.11:5000` will not work from outside.

1. Log in to **Contabo Customer Control Panel**: [https://my.contabo.com](https://my.contabo.com) (or your Contabo login URL).
2. Open your **VPS** (the one with IP `217.217.251.11`).
3. Go to **Firewall** / **Network** / **Security** (name may be “Firewall”, “Security”, or “Network rules” depending on the panel).
4. Add an **inbound** rule:
   - **Protocol:** TCP  
   - **Port:** 5000  
   - **Action:** Allow  
   - **Source:** 0.0.0.0/0 (any) or your IP if you want to restrict access.
5. Save / Apply the rule.

After this, try again from your PC: `http://217.217.251.11:5000`.

---

## 6. Run the App So It Stays Running (Optional)

If you close the Command Prompt or disconnect, the app will stop. To keep it running in the background on the VPS:

### Option A: Run in a separate window and leave it open

1. Open Command Prompt or PowerShell on the VPS.
2. Start the app (e.g. `python main.py` or the `python -c ...` command from step 4).
3. Minimize the window; do not close it. The app keeps running until you close that window or stop the process.

### Option B: Run as a Windows service (advanced)

You can use a tool like **NSSM** (Non-Sucking Service Manager) or **pywin32** to run `python main.py` as a Windows service so it starts automatically and survives reboots. Steps depend on the tool you choose; typically you:

- Point the service to `python.exe` and set the “Application path” to your project folder and “Arguments” to `main.py` (or the script you use).
- Ensure the working directory is the project folder so `FyersCredentials.csv`, `TradeSettings.csv`, and `order_log.csv` are found.

---

## 7. Access the App Remotely via URL

1. Your VPS is reachable at **IP `217.217.251.11`** on **port 5000**.
2. From any device **outside** the VPS (your PC, laptop, or phone), open a browser and go to:
   ```text
   http://217.217.251.11:5000
   ```
3. You should see the **Kapil Spread Algo** Symbol Settings page. Use **Strategy** and **Order Log** from the navbar as on a local install. This URL is the main entry point; no custom hostname is required—the mapping is **IP:port** (`217.217.251.11:5000`).

---

## 8. Security Notes

- The app has **no built-in login**. Anyone who can reach `http://217.217.251.11:5000` can use the UI and, if the strategy is started, can affect trading. So:
  - Prefer a **private network/VPN** or restrict the firewall rule to your IP(s) if your provider supports it.
  - Do not expose the app on the public internet unless you add authentication or run it only in a trusted environment.
- **FyersCredentials.csv** and **TradeSettings.csv** are stored on the VPS; protect RDP and file access so only you (or trusted admins) can log in.
- For production, consider:
  - Using **HTTPS** (e.g. reverse proxy with Nginx/IIS and a certificate).
  - Binding to a non-default port and keeping the firewall rule as restrictive as possible (e.g. only your IP).

---

## 9. Quick Checklist

| Step | Action |
|------|--------|
| 1 | Install Python on Windows VPS and add to PATH |
| 2 | Copy project to VPS, create venv, run `pip install -r requirements.txt` |
| 3 | Add `FyersCredentials.csv` and `TradeSettings.csv` (and `.env` if needed) |
| 4 | Run app with `host=0.0.0.0` and `port=5000` (or adjust `main.py` as in step 4) |
| 5 | Open port **5000** (TCP) in Windows Firewall (Inbound) |
| 6 | From another device, open `http://217.217.251.11:5000` (Symbol Settings page) |
| 7 | (Optional) Run the app as a service or in a persistent window so it stays up |

---

## 10. Troubleshooting

- **Cannot connect from browser when opening http://217.217.251.11:5000**
  - **App must listen on all interfaces:** In `main.py`, use `app.run(host="0.0.0.0", port=5000, ...)`. The project is already set up this way. When the app starts you should see `Running on http://0.0.0.0:5000`.
  - **Windows Firewall:** Confirm an Inbound rule allows TCP port **5000** (see step 5). In **wf.msc** → Inbound Rules, enable **Kapil Spread Algo – Port 5000**.
  - **Contabo firewall (very common cause):** Contabo VPS has a firewall in **my.contabo.com**. Go to your VPS → Firewall / Security and add an **inbound allow** rule for **TCP port 5000**. Without this, the link will not work from outside.
  - The mapping is **217.217.251.11:5000** → Symbol Settings page.
- **App stops when I close the window**
  - Use “Run in background” (Option A in step 6) or install it as a Windows service (Option B).
- **Wrong port**
  - Use the same port in: (1) `app.run(..., port=5000)`, (2) firewall rule, and (3) URL: `http://217.217.251.11:5000`.
