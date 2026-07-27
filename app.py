import os
# Force install the browser and its Linux dependencies
os.system("playwright install chromium")
os.system("playwright install-deps chromium")

import streamlit as st
import streamlit.components.v1 as components
from playwright.async_api import async_playwright
import asyncio
import html
import time
import queue
import threading
import sys
import re
import os
import csv
from datetime import datetime

# ==========================================
# CONFIGURATION & XPATHS
# ==========================================
URL = "https://kumarshekhjournal.com/signal"

# --- TARGET PAIRS FILTER ---
TARGET_PAIRS = [
    # From image_837581.png
    "AUD/NZD (OTC)", "CAD/CHF (OTC)", "NZD/CAD (OTC)", "USD/DZD (OTC)", "USD/PKR (OTC)",
    "EUR/JPY", "EUR/GBP", "USD/ZAR (OTC)", "USD/BRL (OTC)", "CAD/JPY", "EUR/NZD (OTC)", "USD/COP (OTC)",
    # From image_837540.png
    "USD/EGP (OTC)", "USD/MXN (OTC)", "USD/PHP (OTC)", "USD/IDR (OTC)", "USD/NGN (OTC)",
    "GBP/USD", "USD/JPY", "GBP/NZD (OTC)", "NZD/JPY (OTC)", "AUD/CAD", "EUR/AUD", "NZD/CHF (OTC)",
    # From image_83755f.png
    "USD/ARS (OTC)", "USD/BDT (OTC)", "EUR/USD", "AUD/CHF", "AUD/JPY", "GBP/AUD", "GBP/CHF",
    "GBP/JPY", "AUD/USD", "CHF/JPY", "EUR/CAD", "NZD/USD (OTC)", "GBP/CAD"
]

SIGNAL_MENU_XPATH = "/html/body/div/div[2]/aside/nav/div[5]/a/span[3]"
OTC_MARKET_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[1]/div[1]/button[1]"
LIVE_MARKET_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[1]/div[1]/button[2]"
PAIR_BUTTONS_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[1]/div[2]/button"
TIMER_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[2]/label/span/span[2]"
MM_VALUE_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[3]/div[2]/div/div[1]/div/div[2]/span[1]"
NEXT_MINUTE_BUTTON_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[3]/div[2]/div/div[1]/div/div[2]/button[1]"
GENERATE_BUTTON_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[4]/div[4]"
RESULT_CARD_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[1]"
STRENGTH_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[1]/div[3]/span[3]"
DIRECTION_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[1]/div"
RESULT_PAIR_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[2]/p[2]"
TIMEFRAME_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[2]/p[3]"
SUBCARDS_CONTAINER_XPATH = "/html/body/div/div[2]/main/div[2]/div/div/div[5]/div[4]"

# ==========================================
# SINGLE MASTER CSV LOGGING SYSTEM
# ==========================================
def get_or_create_master_csv():
    log_dir = "trading_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    filepath = os.path.join(log_dir, "all_trading_signals.csv")
    
    headers = [
        "Timestamp", "Market", "Pair", "Timeframe", "Strength", 
        "Web Signal", "My Signal (%K/%D)", "%K Value", "%D Value", 
        "Subcards / Live Market Data", "Trade Result"
    ]
    
    if not os.path.exists(filepath):
        try:
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
        except PermissionError:
            st.error("⚠️ Permission Error: Close Excel or file viewers accessing 'all_trading_signals.csv'")
            
    return filepath

def log_signal_to_csv(filepath, signal_data, trade_result):
    subcards_text = " | ".join(signal_data.get("subcards", []))
    
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        signal_data.get("market", ""),
        signal_data.get("pair_name", ""),
        signal_data.get("timeframe", ""),
        signal_data.get("strength", ""),
        signal_data.get("direction", ""),
        signal_data.get("calc_direction", ""),
        signal_data.get("k_val", "N/A"),
        signal_data.get("d_val", "N/A"),
        subcards_text,
        trade_result
    ]
    
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
        return True
    except PermissionError:
        st.error("⚠️ Permission Error: Please CLOSE 'all_trading_signals.csv' in Excel so the app can log your trade result!")
        return False

# ==========================================
# ADVANCED INDICATOR EXTRACTION LOGIC
# ==========================================
def extract_indicators(subcards):
    k_val = None
    d_val = None
    rsi_val = None
    candle_pattern = ""
    
    for card in subcards:
        lower_card = card.lower()
        
        # 1. Extract %K
        match_k = re.search(r'%k\s*\|\s*([0-9.-]+)', lower_card)
        if match_k:
            try: k_val = float(match_k.group(1))
            except: pass
            
        # 2. Extract %D
        match_d = re.search(r'%d\s*\|\s*([0-9.-]+)', lower_card)
        if match_d:
            try: d_val = float(match_d.group(1))
            except: pass
            
        # 3. Extract RSI
        match_rsi = re.search(r'rsi\s*(?:\(\d+\))?\s*\|\s*([0-9.-]+)', lower_card)
        if match_rsi:
            try: rsi_val = float(match_rsi.group(1))
            except: pass
            
        # 4. Extract Candle Pattern
        match_candle = re.search(r'candle\s*\|\s*([^|]+)', lower_card)
        if match_candle:
            candle_pattern = match_candle.group(1).strip()
            
    return k_val, d_val, rsi_val, candle_pattern

# ==========================================
# WINDOWS NOTIFICATION HELPER (CUSTOM GUI)
# ==========================================
def show_windows_notification(pair_name, direction, timeframe, strength, market, subcards=None, calc_direction="N/A"):
    if subcards is None:
        subcards = []
        
    try:
        from plyer import notification
        notification.notify(
            title=f"🎯 {calc_direction} Signal ({market})!",
            message=f"Pair: {pair_name}\nWebsite: {direction}\nYours: {calc_direction}",
            app_name="Signal Scanner",
            timeout=10
        )
    except: pass

    if sys.platform == "win32":
        def persistent_alert():
            import tkinter as tk
            from tkinter import font
            
            root = tk.Tk()
            root.title(f"Signal Alert - {market}")
            root.configure(bg="#121216")
            root.attributes("-topmost", True)
            
            w = 560
            h = min(360 + (len(subcards) * 40), 600) if subcards else 360
            ws = root.winfo_screenwidth()
            hs = root.winfo_screenheight()
            x = (ws/2) - (w/2)
            y = (hs/2) - (h/2)
            root.geometry(f'{w}x{int(h)}+{int(x)}+{int(y)}')
            
            is_up = "BUY" in direction.upper() or "CALL" in direction.upper()
            dir_color = "#00e676" if is_up else "#ff1744"
            arrow = "📈 BUY" if is_up else "📉 SELL"
            
            calc_is_up = "BUY" in calc_direction.upper() or "CALL" in calc_direction.upper()
            calc_dir_color = "#00e676" if calc_is_up else "#ff1744"
            if "N/A" in calc_direction.upper() or "NEUTRAL" in calc_direction.upper(): 
                calc_dir_color = "#d4d4d8"
                calc_arrow = "➖ N/A"
            else:
                calc_arrow = "📈 BUY" if calc_is_up else "📉 SELL"

            market_color = "#a855f7" if market == "OTC" else "#3b82f6"
            
            font_title = font.Font(family="Segoe UI", size=15, weight="bold")
            font_pair = font.Font(family="Segoe UI", size=13)
            font_dir = font.Font(family="Segoe UI", size=24, weight="bold")
            font_btn = font.Font(family="Segoe UI", size=11, weight="bold")
            font_sub = font.Font(family="Segoe UI", size=10)
            
            header = tk.Frame(root, bg=market_color)
            header.pack(fill="x", pady=(0, 10))
            tk.Label(header, text=f"{market} MARKET ALERT", font=font_btn, bg=market_color, fg="white", pady=6).pack()

            tk.Label(root, text=f"🎯 {strength} SIGNAL FOUND!", font=font_title, bg="#121216", fg="#ffffff").pack(pady=2)
            tk.Label(root, text=f"Pair: {pair_name}   |   Timeframe: {timeframe}", font=font_pair, bg="#121216", fg="#d4d4d8").pack(pady=2)
            
            signals_frame = tk.Frame(root, bg="#121216")
            signals_frame.pack(fill="x", pady=15, padx=20)
            
            left_frame = tk.Frame(signals_frame, bg="#1e1e28", highlightbackground="#27272a", highlightthickness=1, padx=20, pady=10)
            left_frame.pack(side="left", expand=True)
            tk.Label(left_frame, text="WEB SIGNAL", font=font_btn, bg="#1e1e28", fg="#a1a1aa").pack()
            tk.Label(left_frame, text=arrow, font=font_dir, bg="#1e1e28", fg=dir_color).pack(pady=5)
            
            right_frame = tk.Frame(signals_frame, bg="#1e1e28", highlightbackground="#27272a", highlightthickness=1, padx=20, pady=10)
            right_frame.pack(side="right", expand=True)
            tk.Label(right_frame, text="MY SIGNAL (%K/%D)", font=font_btn, bg="#1e1e28", fg="#a1a1aa").pack()
            tk.Label(right_frame, text=calc_arrow, font=font_dir, bg="#1e1e28", fg=calc_dir_color).pack(pady=5)
            
            if subcards:
                text_area = tk.Text(root, bg="#1e1e28", fg="#e4e4e7", font=font_sub, wrap="word", relief="flat", height=4)
                text_area.pack(fill="both", expand=True, padx=20, pady=5)
                for idx, sc in enumerate(subcards, 1):
                    text_area.insert("end", f"#{idx}: {sc}\n\n")
                text_area.config(state="disabled")

            def on_close():
                root.destroy()
                
            btn = tk.Button(root, text="ACKNOWLEDGE", font=font_btn, bg="#27272a", fg="white",
                            activebackground="#3f3f46", activeforeground="white",
                            command=on_close, relief="flat", cursor="hand2")
            btn.pack(ipadx=24, ipady=8, pady=10)
            root.lift()
            root.focus_force()
            root.mainloop()
            
        threading.Thread(target=persistent_alert).start()

# ==========================================
# PLAYWRIGHT ASYNC FUNCTIONS
# ==========================================
async def get_text(page, xpath, timeout=10000):
    locator = page.locator(f"xpath={xpath}")
    await locator.wait_for(state="visible", timeout=timeout)
    return (await locator.inner_text()).strip()

async def click_xpath(page, xpath, timeout=10000):
    locator = page.locator(f"xpath={xpath}")
    await locator.wait_for(state="visible", timeout=timeout)
    await locator.click()
    
async def fetch_subcards_data(page):
    subcards = []
    try:
        container = page.locator(f"xpath={SUBCARDS_CONTAINER_XPATH}")
        await container.wait_for(state="visible", timeout=4000)
        children = container.locator("> div")
        count = await children.count()
        if count > 0:
            for i in range(count):
                txt = (await children.nth(i).inner_text()).strip()
                if txt:
                    cleaned_txt = " | ".join([line.strip() for line in txt.split("\n") if line.strip()])
                    subcards.append(cleaned_txt)
        else:
            raw_text = (await container.inner_text()).strip()
            if raw_text:
                subcards = [line.strip() for line in raw_text.split("\n") if line.strip()]
    except Exception:
        pass
    return subcards

async def login_and_setup(page, email, password, status_queue, market_type):
    status_queue.put({"type": "STATUS", "msg": f"Logging in to {market_type} session..."})
    await page.goto(URL, wait_until="domcontentloaded")
    await page.locator("input[type='email'], input[name='email']").fill(email)
    await page.locator("input[type='password'], input[name='password']").fill(password)
    await page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)
    await click_xpath(page, SIGNAL_MENU_XPATH, timeout=10000)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)
    if market_type == "LIVE":
        status_queue.put({"type": "STATUS", "msg": "Switching to LIVE Market..."})
        await click_xpath(page, LIVE_MARKET_XPATH, timeout=10000)
    else:
        status_queue.put({"type": "STATUS", "msg": "Switching to OTC Market..."})
        await click_xpath(page, OTC_MARKET_XPATH, timeout=10000)
    await page.wait_for_timeout(2000)

def get_timer_minute(timer_text):
    parts = timer_text.strip().split(":")
    if len(parts) != 3: return 0
    return int(parts[1])

def get_selected_minute(mm_text):
    digits = "".join(ch for ch in mm_text if ch.isdigit())
    if not digits: return 0
    return int(digits)

async def adjust_next_minute_if_needed(page):
    for _ in range(60):
        timer_text = await get_text(page, TIMER_XPATH)
        selected_mm_text = await get_text(page, MM_VALUE_XPATH)
        if (get_selected_minute(selected_mm_text) - get_timer_minute(timer_text)) % 60 == 2:
            return
        await click_xpath(page, NEXT_MINUTE_BUTTON_XPATH)
        await page.wait_for_timeout(400)
    raise Exception("Could not set minute 2 mins ahead.")

async def bot_market_loop(email, password, market_type, status_queue, pause_event, stop_event, win_pos):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=50,
            args=[f'--window-size=1280,800', f'--window-position={win_pos}', '--no-viewport']
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            await login_and_setup(page, email, password, status_queue, market_type)
        except Exception as e:
            status_queue.put({"type": "ERROR", "msg": f"{market_type} Login failed: {str(e)}"})
            await browser.close()
            return

        scan_from_end_next = False

        while not stop_event.is_set():
            try:
                if market_type == "LIVE": await click_xpath(page, LIVE_MARKET_XPATH)
                else: await click_xpath(page, OTC_MARKET_XPATH)
                await page.wait_for_timeout(1000)

                pair_buttons = page.locator(f"xpath={PAIR_BUTTONS_XPATH}")
                await pair_buttons.first.wait_for(state="visible", timeout=15000)
                pair_count = await pair_buttons.count()
                indexes = list(range(pair_count)) if not scan_from_end_next else list(range(pair_count - 1, -1, -1))
                status_queue.put({"type": "STATUS", "msg": f"Starting 1-by-1 scan on TARGET pairs only..."})
                signal_found = False

                for idx in indexes:
                    while pause_event.is_set() and not stop_event.is_set():
                        await asyncio.sleep(0.5)
                    if stop_event.is_set(): break

                    pair = pair_buttons.nth(idx)
                    pair_name = (await pair.inner_text()).strip()

                    if pair_name not in TARGET_PAIRS:
                        continue
                        
                    status_queue.put({"type": "STATUS", "msg": f"Checking {pair_name} ({idx+1}/{pair_count})..."})
                    await pair.click()
                    await page.wait_for_timeout(1000)

                    await adjust_next_minute_if_needed(page)
                    await click_xpath(page, GENERATE_BUTTON_XPATH)
                    
                    status_queue.put({"type": "STATUS", "msg": f"Generating {pair_name}... (Waiting for UI update)"})
                    await page.wait_for_timeout(6000)
                    
                    await page.locator(f"xpath={STRENGTH_XPATH}").wait_for(state="visible", timeout=20000)
                    strength = (await get_text(page, STRENGTH_XPATH)).upper()

                    if "STRONG" in strength and "MODERATE" not in strength and "WEAK" not in strength:
                        direction = (await get_text(page, DIRECTION_XPATH)).upper()
                        timeframe = await get_text(page, TIMEFRAME_XPATH)
                        subcards = await fetch_subcards_data(page)
                        
                        # 1. Extract all Custom Indicators
                        k_val, d_val, rsi_val, candle_pattern = extract_indicators(subcards)
                        calc_direction = "N/A"
                        
                        if k_val is not None and d_val is not None:
                            if k_val > d_val:
                                calc_direction = "BUY / CALL"
                            elif k_val < d_val:
                                calc_direction = "PUT / SELL"
                            else:
                                calc_direction = "NEUTRAL"
                                
                        # Use Custom Direction to determine BUY/SELL tests (Fall back to Web Direction if Custom is N/A)
                        active_signal = calc_direction if calc_direction not in ["N/A", "NEUTRAL"] else direction
                        is_buy = "BUY" in active_signal or "CALL" in active_signal
                        is_sell = "PUT" in active_signal or "SELL" in active_signal

                        skip_reason = None
                        
                        # ==========================================
                        # APPLY STRICT TRADE FILTERS
                        # ==========================================
                        
                        # Filter A: Stochastic Logic
                        if k_val is not None and d_val is not None:
                            if k_val >= 80 and d_val >= 80:
                                skip_reason = f"%K & %D are >= 80"
                            elif abs(k_val - d_val) < 3:
                                skip_reason = f"Weak Stoch crossover (|%K-%D| = {round(abs(k_val - d_val), 2)} < 3)"

                        # Filter B: Candle Constraints
                        if skip_reason is None:
                            candle_lower = candle_pattern.lower()
                            if "doji" in candle_lower or "neutral" in candle_lower:
                                skip_reason = "Candle is Doji or Neutral"
                            elif "bullish engulfing" in candle_lower and not is_buy:
                                skip_reason = "Bullish Engulfing but signal is not BUY"
                            elif "bearish engulfing" in candle_lower and not is_sell:
                                skip_reason = "Bearish Engulfing but signal is not SELL"
                            elif "pin bar wick up" in candle_lower and not is_sell:
                                skip_reason = "Pin Bar Wick Up but signal is not SELL"
                            elif "pin bar wick down" in candle_lower and not is_buy:
                                skip_reason = "Pin Bar Wick Down but signal is not BUY"

                        # Filter C: Strict RSI Limits
                        if skip_reason is None:
                            if rsi_val is not None:
                                if is_buy and rsi_val >= 30:
                                    skip_reason = f"BUY signal but RSI ({rsi_val}) is not < 30"
                                elif is_sell and rsi_val <= 70:
                                    skip_reason = f"SELL signal but RSI ({rsi_val}) is not > 70"
                            else:
                                skip_reason = "Missing RSI Data (Cannot verify constraints)"

                        # Apply Skip if ANY filter failed
                        if skip_reason:
                            status_queue.put({"type": "STATUS", "msg": f"Skipped {pair_name} - {skip_reason}"})
                            continue
                            
                        # If passed all rules, proceed to alert!
                        status_queue.put({"type": "STATUS", "msg": f"{strength} signal found on {pair_name}!"})
                        result_data = {
                            "direction": direction, "pair_name": pair_name,
                            "timeframe": timeframe, "strength": strength, 
                            "market": market_type, "subcards": subcards,
                            "calc_direction": calc_direction,
                            "k_val": k_val, "d_val": d_val
                        }
                        status_queue.put({"type": "SIGNAL", "data": result_data})
                        signal_found = True
                        pause_event.set()
                        scan_from_end_next = not scan_from_end_next
                        break
                    else:
                        status_queue.put({"type": "STATUS", "msg": f"Skipped {pair_name} - Signal was '{strength}' (Not Strong)"})
                        
                if not signal_found and not stop_event.is_set():
                    status_queue.put({"type": "STATUS", "msg": "All target pairs scanned. Restarting..."})
                    scan_from_end_next = False
                    await asyncio.sleep(1)

            except Exception as e:
                status_queue.put({"type": "ERROR", "msg": f"Error: {str(e)}"})
                await page.reload(wait_until="domcontentloaded")
                await login_and_setup(page, email, password, status_queue, market_type)

        await browser.close()
        status_queue.put({"type": "STATUS", "msg": "Bot Stopped."})

def run_bot_thread(email, password, market, queue, pause_ev, stop_ev, win_pos):
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_market_loop(email, password, market, queue, pause_ev, stop_ev, win_pos))
    except Exception as e:
        queue.put({"type": "ERROR", "msg": f"Crash: {str(e)}"})

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Dual Independent Scanner", layout="wide")

# Single Master CSV Path
if "csv_filename" not in st.session_state:
    st.session_state["csv_filename"] = get_or_create_master_csv()

markets = ["OTC", "LIVE"]
for m in markets:
    if f"{m}_queue" not in st.session_state:
        st.session_state[f"{m}_queue"] = queue.Queue()
        st.session_state[f"{m}_pause"] = threading.Event()
        st.session_state[f"{m}_stop"] = threading.Event()
        st.session_state[f"{m}_running"] = False
        st.session_state[f"{m}_signal"] = None
        st.session_state[f"{m}_status"] = "Ready to start."
        st.session_state[f"{m}_notified"] = False

def generate_html_card(result_data):
    direction = result_data.get("direction", "").upper()
    calc_direction = result_data.get("calc_direction", "N/A").upper()
    subcards = result_data.get("subcards", [])
    
    is_up = "BUY" in direction or "CALL" in direction
    if is_up:
        border_color = "#00e676"
        anim_name = "pulse-green"
        text_color = "#00e676"
        glow_color = "rgba(0, 230, 118, 0.4)"
        icon = "📈 BUY"
    else:
        border_color = "#ff1744"
        anim_name = "pulse-red"
        text_color = "#ff1744"
        glow_color = "rgba(255, 23, 68, 0.4)"
        icon = "📉 SELL"
        
    calc_is_up = "BUY" in calc_direction or "CALL" in calc_direction
    if "N/A" in calc_direction or "NEUTRAL" in calc_direction:
        calc_text_color = "#d4d4d8"
        calc_glow = "rgba(212, 212, 216, 0.2)"
        calc_icon = "➖ N/A"
    else:
        calc_text_color = "#00e676" if calc_is_up else "#ff1744"
        calc_glow = "rgba(0, 230, 118, 0.4)" if calc_is_up else "rgba(255, 23, 68, 0.4)"
        calc_icon = "📈 BUY" if calc_is_up else "📉 SELL"
        
    badge_bg = "linear-gradient(90deg, #9333ea, #a855f7)" if result_data["market"] == "OTC" else "linear-gradient(90deg, #2563eb, #3b82f6)"
    
    subcards_html = ""
    if subcards:
        subcards_html = "<div class='subcards-section'><div class='subcards-title'>📊 Subcards Analysis</div>"
        for idx, sc in enumerate(subcards, 1):
            subcards_html += f"<div class='subcard-item'><span class='subcard-num'>#{idx}</span> {html.escape(sc)}</div>"
        subcards_html += "</div>"

    return f"""
    <style>
    @keyframes pulse-green {{
    0% {{ box-shadow: 0 0 15px rgba(0, 230, 118, 0.3); }}
    50% {{ box-shadow: 0 0 35px rgba(0, 230, 118, 0.6); transform: scale(1.01); }}
    100% {{ box-shadow: 0 0 15px rgba(0, 230, 118, 0.3); }}
    }}
    @keyframes pulse-red {{
    0% {{ box-shadow: 0 0 15px rgba(255, 23, 68, 0.3); }}
    50% {{ box-shadow: 0 0 35px rgba(255, 23, 68, 0.6); transform: scale(1.01); }}
    100% {{ box-shadow: 0 0 15px rgba(255, 23, 68, 0.3); }}
    }}
    .signal-card {{
    background: linear-gradient(145deg, #1e1e28, #14141a);
    border: 2px solid {border_color};
    border-radius: 24px;
    padding: 30px;
    color: #ffffff;
    font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    text-align: center;
    position: relative;
    animation: {anim_name} 2s infinite ease-in-out;
    transition: transform 0.3s ease;
    max-width: 500px;
    margin: auto;
    }}
    .market-badge {{
    position: absolute;
    top: 0; right: 0; background: {badge_bg}; padding: 8px 24px;
    border-bottom-left-radius: 20px; border-top-right-radius: 20px;
    font-weight: 800; font-size: 14px; letter-spacing: 1px;
    }}
    .direction-label {{
    color: #8b8b9e; font-size: 11px; font-weight: 700;
    letter-spacing: 2px; text-transform: uppercase; margin-top: 15px;
    }}
    .direction-value {{
    font-size: 32px; font-weight: 900; margin: 10px 0 25px;
    }}
    .data-row {{
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px; padding: 12px 22px; margin-top: 14px;
    display: flex; justify-content: space-between; align-items: center;
    }}
    .row-label {{ color: #a1a1aa; font-weight: 600; font-size: 14px; text-transform: uppercase; }}
    .row-value {{ font-size: 20px; font-weight: 800; color: #fff; }}
    .subcards-section {{
        margin-top: 16px; text-align: left; background: rgba(0,0,0,0.2);
        padding: 12px; border-radius: 12px; max-height: 160px; overflow-y: auto;
    }}
    .subcards-title {{ font-size: 12px; font-weight: 800; color: #a1a1aa; margin-bottom: 8px; text-transform: uppercase; }}
    .subcard-item {{ font-size: 12px; color: #d4d4d8; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
    .subcard-num {{ color: #a855f7; font-weight: bold; margin-right: 6px; }}
    </style>
    <div class="signal-card">
    <div class="market-badge">{html.escape(result_data["market"])} MARKET</div>
    
    <div style="display: flex; justify-content: space-between; background: rgba(0,0,0,0.2); border-radius: 16px; padding: 10px; margin-bottom: 20px; margin-top: 10px;">
        <div style="flex: 1; text-align: center; border-right: 1px solid rgba(255,255,255,0.1);">
            <div class="direction-label">Web Signal</div>
            <div class="direction-value" style="color: {text_color}; text-shadow: 0 0 25px {glow_color};">
                {icon}
            </div>
        </div>
        <div style="flex: 1; text-align: center;">
            <div class="direction-label">My Signal (%K/%D)</div>
            <div class="direction-value" style="color: {calc_text_color}; text-shadow: 0 0 25px {calc_glow};">
                {calc_icon}
            </div>
        </div>
    </div>

    <div class="data-row">
    <span class="row-label">Pair</span>
    <span class="row-value">{html.escape(result_data["pair_name"])}</span>
    </div>
    <div class="data-row">
    <span class="row-label">Timeframe</span>
    <span class="row-value">{html.escape(result_data["timeframe"])}</span>
    </div>
    
    {subcards_html}
    </div>
    """

st.title("🚀 Independent Market Scanners")

with st.sidebar:
    st.header("Credentials")
    email_input = st.text_input("Email", value="mayurlohar333@gmail.com")
    pass_input = st.text_input("Password", type="password", value="mayur.....")
    st.divider()
    
    st.header("📁 Master CSV Storage")
    st.code(st.session_state["csv_filename"], language="text")
    st.info("All trades across all sessions are appended continuously into this file.")
    st.divider()

col1, col2 = st.columns(2)

with col1:
    st.header("🟪 OTC Scanner")
    if not st.session_state["OTC_running"]:
        if st.button("▶️ Scan OTC Market", use_container_width=True, type="primary"):
            st.session_state["OTC_stop"].clear()
            st.session_state["OTC_pause"].clear()
            st.session_state["OTC_running"] = True
            st.session_state["OTC_signal"] = None
            st.session_state["OTC_notified"] = False
            threading.Thread(target=run_bot_thread, args=(email_input, pass_input, "OTC", st.session_state["OTC_queue"], st.session_state["OTC_pause"], st.session_state["OTC_stop"], "0,0"), daemon=True).start()
            st.rerun()
    else:
        if st.button("🛑 Stop OTC Scanner", use_container_width=True):
            st.session_state["OTC_stop"].set()
            st.session_state["OTC_pause"].set()
            st.session_state["OTC_running"] = False
            st.rerun()

with col2:
    st.header("🟦 LIVE Scanner")
    if not st.session_state["LIVE_running"]:
        if st.button("▶️ Scan Live Market", use_container_width=True, type="primary"):
            st.session_state["LIVE_stop"].clear()
            st.session_state["LIVE_pause"].clear()
            st.session_state["LIVE_running"] = True
            st.session_state["LIVE_signal"] = None
            st.session_state["LIVE_notified"] = False
            threading.Thread(target=run_bot_thread, args=(email_input, pass_input, "LIVE", st.session_state["LIVE_queue"], st.session_state["LIVE_pause"], st.session_state["LIVE_stop"], "100,100"), daemon=True).start()
            st.rerun()
    else:
        if st.button("🛑 Stop Live Scanner", use_container_width=True):
            st.session_state["LIVE_stop"].set()
            st.session_state["LIVE_pause"].set()
            st.session_state["LIVE_running"] = False
            st.rerun()

st.divider()

# --- PROCESS QUEUES ---
for m in markets:
    while not st.session_state[f"{m}_queue"].empty():
        msg = st.session_state[f"{m}_queue"].get()
        if msg["type"] == "STATUS": st.session_state[f"{m}_status"] = msg["msg"]
        elif msg["type"] == "ERROR": st.error(f"{m} Error: " + msg["msg"])
        elif msg["type"] == "SIGNAL": st.session_state[f"{m}_signal"] = msg["data"]

# --- DISPLAY UI STATUS & WIN/LOSS CONTROLS ---
display_cols = st.columns(2)

for i, m in enumerate(markets):
    with display_cols[i]:
        if st.session_state[f"{m}_signal"]:
            sig = st.session_state[f"{m}_signal"]
            if not st.session_state[f"{m}_notified"]:
                show_windows_notification(
                    sig["pair_name"], 
                    sig["direction"], 
                    sig["timeframe"], 
                    sig["strength"], 
                    sig["market"],
                    sig.get("subcards", []),
                    sig.get("calc_direction", "N/A")
                )
                st.toast(f"{sig['strength']} Signal on {sig['pair_name']} ({m})!", icon='🎯')
                st.session_state[f"{m}_notified"] = True

            st.success(f"🎯 {sig['strength']} Signal Found!")
            components.html(generate_html_card(sig), height=620)
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            
            with btn_col1:
                if st.button("✅ WIN", type="primary", use_container_width=True, key=f"win_{m}"):
                    if log_signal_to_csv(st.session_state["csv_filename"], sig, "WIN"):
                        st.toast(f"Logged WIN for {sig['pair_name']}!", icon="🎉")
                        st.session_state[f"{m}_signal"] = None
                        st.session_state[f"{m}_notified"] = False
                        st.session_state[f"{m}_pause"].clear()
                        st.rerun()
                    
            with btn_col2:
                if st.button("❌ LOSS", use_container_width=True, key=f"loss_{m}"):
                    if log_signal_to_csv(st.session_state["csv_filename"], sig, "LOSS"):
                        st.toast(f"Logged LOSS for {sig['pair_name']}!", icon="⚠️")
                        st.session_state[f"{m}_signal"] = None
                        st.session_state[f"{m}_notified"] = False
                        st.session_state[f"{m}_pause"].clear()
                        st.rerun()
                    
            with btn_col3:
                if st.button("⏭️ SKIP", use_container_width=True, key=f"skip_{m}"):
                    if log_signal_to_csv(st.session_state["csv_filename"], sig, "SKIPPED"):
                        st.session_state[f"{m}_signal"] = None
                        st.session_state[f"{m}_notified"] = False
                        st.session_state[f"{m}_pause"].clear()
                        st.rerun()

        elif st.session_state[f"{m}_running"]:
            st.info(f"🔄 {m} Bot is scanning...")
            st.code(st.session_state[f"{m}_status"], language="text")
        else:
            st.write(f"💤 {m} Bot is offline.")

if st.session_state["OTC_running"] or st.session_state["LIVE_running"]:
    time.sleep(1)
    st.rerun()


    # python -m streamlit run "C:\Users\DELL-L5420\Desktop\New folder (2)\Kumar.py"
