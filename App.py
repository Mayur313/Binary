import streamlit as st
import streamlit.components.v1 as components
from playwright.async_api import async_playwright
from pathlib import Path
import asyncio
import html
import os
import time
import queue
import threading
import sys

# ==========================================
# CONFIGURATION & XPATHS
# ==========================================
URL = "https://kumarshekhjournal.com/signal"
BATCH_SIZE = 3

SIGNAL_MENU_XPATH = "/html/body/div/div[1]/aside/nav/div[5]/a"
PAIR_BUTTONS_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[4]/div[1]/div[2]/button"
TIMER_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[4]/div[2]/label/span/span[2]"
MM_VALUE_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[4]/div[3]/div[2]/div/div[1]/div/div[2]/span[1]"
NEXT_MINUTE_BUTTON_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[4]/div[3]/div[2]/div/div[1]/div/div[2]/button[1]"
GENERATE_BUTTON_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[4]/div[4]"
RESULT_CARD_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[5]/div[1]"
STRENGTH_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[5]/div[1]/div[3]/span[3]"

DIRECTION_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[1]/div"
RESULT_PAIR_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[2]/p[2]"
TIMEFRAME_XPATH = "/html/body/div/div[1]/main/div[2]/div/div/div[5]/div[1]/div[1]/div[2]/p[3]"

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

async def login(page, email, password, status_queue):
    status_queue.put({"type": "STATUS", "msg": "Logging in..."})
    await page.goto(URL, wait_until="domcontentloaded")
    await page.locator("input[type='email'], input[name='email']").fill(email)
    await page.locator("input[type='password'], input[name='password']").fill(password)
    await page.locator("button[type='submit'], button:has-text('Login'), button:has-text('Sign in')").click()
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(3000)
    await click_xpath(page, SIGNAL_MENU_XPATH)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(2000)

async def open_signal_page(page):
    await page.goto(URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)
    try:
        await click_xpath(page, SIGNAL_MENU_XPATH, timeout=5000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)
    except Exception:
        pass

def get_timer_minute(timer_text):
    parts = timer_text.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Timer is not in HH:MM:SS format: {timer_text}")
    return int(parts[1])

def get_selected_minute(mm_text):
    digits = "".join(ch for ch in mm_text if ch.isdigit())
    if not digits:
        raise ValueError(f"No number found in minute text: {mm_text}")
    return int(digits)

async def adjust_next_minute_if_needed(page, status_queue):
    for attempt in range(60):
        timer_text = await get_text(page, TIMER_XPATH)
        current_timer_mm = get_timer_minute(timer_text)
        selected_mm_text = await get_text(page, MM_VALUE_XPATH)
        selected_mm = get_selected_minute(selected_mm_text)

        difference = (selected_mm - current_timer_mm) % 60
        if difference == 2:
            return
        
        await click_xpath(page, NEXT_MINUTE_BUTTON_XPATH)
        await page.wait_for_timeout(400)
    raise Exception("Could not set selected minute exactly 2 minutes ahead.")

async def generate_and_check_strength(page):
    await click_xpath(page, GENERATE_BUTTON_XPATH)
    await page.locator(f"xpath={RESULT_CARD_XPATH}").wait_for(state="visible", timeout=20000)
    await page.locator(f"xpath={STRENGTH_XPATH}").wait_for(state="visible", timeout=20000)
    await page.wait_for_timeout(1500)
    strength = (await get_text(page, STRENGTH_XPATH, timeout=20000)).upper()
    return strength

async def get_result_popup_data(page):
    direction = (await get_text(page, DIRECTION_XPATH, timeout=15000)).upper()
    pair_name = await get_text(page, RESULT_PAIR_XPATH, timeout=15000)
    timeframe = await get_text(page, TIMEFRAME_XPATH, timeout=15000)
    return {"direction": direction, "pair_name": pair_name, "timeframe": timeframe}

async def get_pair_count(page):
    pair_buttons = page.locator(f"xpath={PAIR_BUTTONS_XPATH}")
    await pair_buttons.first.wait_for(state="visible", timeout=15000)
    return await pair_buttons.count()

async def select_pair_by_index(page, index):
    pair_buttons = page.locator(f"xpath={PAIR_BUTTONS_XPATH}")
    await pair_buttons.first.wait_for(state="visible", timeout=15000)
    count = await pair_buttons.count()
    if index < 0 or index >= count:
        return None
    pair = pair_buttons.nth(index)
    pair_name = (await pair.inner_text()).strip()
    await pair.click()
    await page.wait_for_timeout(1000)
    return pair_name

async def check_one_pair(context, index, status_queue):
    page = await context.new_page()
    try:
        await open_signal_page(page)
        pair_name = await select_pair_by_index(page, index)
        if pair_name is None:
            await page.close()
            return {"index": index, "strong": False, "error": "Pair not found"}
        
        await adjust_next_minute_if_needed(page, status_queue)
        strength = await generate_and_check_strength(page)

        if strength == "STRONG":
            status_queue.put({"type": "STATUS", "msg": f"STRONG signal found on {pair_name}!"})
            result_data = await get_result_popup_data(page)
            return {"index": index, "pair_name": pair_name, "strong": True, "result_data": result_data, "page": page}
        
        await page.close()
        return {"index": index, "pair_name": pair_name, "strong": False}

    except Exception as e:
        try:
            await page.close()
        except Exception:
            pass
        return {"index": index, "strong": False, "error": str(e)}

async def scan_pairs_batch(context, pair_count, start_index, step, status_queue, stop_event):
    if step == 1:
        indexes = list(range(start_index, pair_count))
    else:
        indexes = list(range(start_index, -1, -1))

    position = 0
    while position < len(indexes):
        if stop_event.is_set():
            return None

        batch_indexes = indexes[position:position + BATCH_SIZE]
        status_queue.put({"type": "STATUS", "msg": f"Checking batch pairs: {[i + 1 for i in batch_indexes]}"})

        results = await asyncio.gather(*[check_one_pair(context, index, status_queue) for index in batch_indexes])
        strong_results = [result for result in results if result.get("strong")]

        if strong_results:
            first_strong = strong_results[0]
            for result in results:
                if result is not first_strong and result.get("page"):
                    try: await result["page"].close()
                    except Exception: pass
            
            return first_strong

        position += BATCH_SIZE
        await asyncio.sleep(1)

    status_queue.put({"type": "STATUS", "msg": "All pairs scanned. STRONG not found."})
    return None

async def bot_main_loop(email, password, status_queue, pause_event, stop_event):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=150,
            args=['--window-size=800,600', '--window-position=0,0']
        )
        context = await browser.new_context(viewport={'width': 800, 'height': 600})
        main_page = await context.new_page()

        try:
            await login(main_page, email, password, status_queue)
        except Exception as e:
            status_queue.put({"type": "ERROR", "msg": f"Login failed: {str(e)}"})
            await browser.close()
            return

        scan_from_end_next = False

        while not stop_event.is_set():
            try:
                pair_count = await get_pair_count(main_page)
                if scan_from_end_next:
                    status_queue.put({"type": "STATUS", "msg": "Starting scan from last to first pair..."})
                    strong_result = await scan_pairs_batch(context, pair_count, pair_count - 1, -1, status_queue, stop_event)
                else:
                    status_queue.put({"type": "STATUS", "msg": "Starting scan from first to last pair..."})
                    strong_result = await scan_pairs_batch(context, pair_count, 0, 1, status_queue, stop_event)

                if stop_event.is_set():
                    break

                if strong_result is None:
                    status_queue.put({"type": "STATUS", "msg": "Restarting automatically..."})
                    scan_from_end_next = False
                    await asyncio.sleep(1)
                    continue

                status_queue.put({"type": "SIGNAL", "data": strong_result["result_data"]})
                
                while not pause_event.is_set() and not stop_event.is_set():
                    await asyncio.sleep(0.5)
                
                pause_event.clear()
                scan_from_end_next = True

                try:
                    await strong_result["page"].close()
                except:
                    pass

            except Exception as e:
                status_queue.put({"type": "ERROR", "msg": f"Error in main loop: {str(e)}"})
                await asyncio.sleep(2)

        await browser.close()
        status_queue.put({"type": "STATUS", "msg": "Bot Stopped."})

def run_bot_thread(email, password, status_queue, pause_event, stop_event):
    # This is the crucial fix for Windows asyncio subprocesses in threads
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(bot_main_loop(email, password, status_queue, pause_event, stop_event))
    except Exception as e:
        status_queue.put({"type": "ERROR", "msg": f"Thread crashed: {str(e)}"})

# ==========================================
# STREAMLIT UI
# ==========================================
st.set_page_config(page_title="Signal Scanner", layout="centered")

if "status_queue" not in st.session_state:
    st.session_state.status_queue = queue.Queue()
    st.session_state.pause_event = threading.Event()
    st.session_state.stop_event = threading.Event()
    st.session_state.bot_running = False
    st.session_state.current_signal = None
    st.session_state.last_status = "Ready to start."

def generate_html_card(result_data):
    direction = result_data["direction"]
    pair_name = result_data["pair_name"]
    timeframe = result_data["timeframe"]
    is_up = "BUY / CALL" in direction
    direction_color = "#00c853" if is_up else "#ff1744"
    direction_shadow = "rgba(0, 200, 83, 0.45)" if is_up else "rgba(255, 23, 68, 0.45)"
    arrow = "BUY / CALL" if is_up else "PUT / SELL"

    return f"""
    <div style="
        background: #121216; border: 1px solid {direction_color}; border-radius: 18px; 
        padding: 28px; box-shadow: 0 0 36px {direction_shadow}; color: white; 
        font-family: Arial, sans-serif; text-align: center; width: 100%; max-width: 400px; margin: auto;">
        <div style="color: #a1a1aa; font-size: 12px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px;">Signal Direction</div>
        <div style="color: {direction_color}; font-size: 40px; font-weight: 900; margin: 18px 0 26px; text-shadow: 0 0 22px {direction_shadow};">{html.escape(arrow)}</div>
        <div style="background: #1c1c22; border-radius: 12px; padding: 16px; margin-top: 14px; border: 1px solid #2f2f38; display: flex; justify-content: space-between;">
            <span style="color: #a1a1aa; font-weight: bold;">Pair</span>
            <span style="font-size: 20px; font-weight: 800;">{html.escape(pair_name)}</span>
        </div>
        <div style="background: #1c1c22; border-radius: 12px; padding: 16px; margin-top: 14px; border: 1px solid #2f2f38; display: flex; justify-content: space-between;">
            <span style="color: #a1a1aa; font-weight: bold;">Timeframe</span>
            <span style="font-size: 20px; font-weight: 800;">{html.escape(timeframe)}</span>
        </div>
        <div style="margin-top: 22px; padding: 12px; border-radius: 999px; background: rgba(34, 197, 94, 0.12); color: #22c55e; font-weight: 900; letter-spacing: 1px;">
            STRONG SIGNAL
        </div>
    </div>
    """

st.title("🚀 Automated Signal Scanner")

with st.sidebar:
    st.header("Credentials")
    email_input = st.text_input("Email", value="mayurlohar333@gmail.com")
    pass_input = st.text_input("Password", type="password", value="mayur.....")
    
    st.divider()
    
    if not st.session_state.bot_running:
        if st.button("▶️ Start Scanner", use_container_width=True, type="primary"):
            st.session_state.stop_event.clear()
            st.session_state.pause_event.clear()
            st.session_state.bot_running = True
            st.session_state.current_signal = None
            
            t = threading.Thread(
                target=run_bot_thread, 
                args=(email_input, pass_input, st.session_state.status_queue, st.session_state.pause_event, st.session_state.stop_event),
                daemon=True
            )
            t.start()
            st.rerun()
    else:
        if st.button("🛑 Stop Scanner", use_container_width=True):
            st.session_state.stop_event.set()
            st.session_state.pause_event.set() 
            st.session_state.bot_running = False
            st.rerun()

# --- Main Area Display ---

while not st.session_state.status_queue.empty():
    msg = st.session_state.status_queue.get()
    if msg["type"] == "STATUS":
        st.session_state.last_status = msg["msg"]
    elif msg["type"] == "ERROR":
        st.error(msg["msg"])
    elif msg["type"] == "SIGNAL":
        st.session_state.current_signal = msg["data"]

if st.session_state.current_signal:
    st.success("🎯 STRONG Signal Found!")
    
    card_html = generate_html_card(st.session_state.current_signal)
    components.html(card_html, height=450)
    
    if st.button("⏭️ Continue Scanning (Reverse Order)", type="primary", use_container_width=True):
        st.session_state.current_signal = None
        st.session_state.pause_event.set()
        st.rerun()

elif st.session_state.bot_running:
    st.info("🔄 Bot is currently running...")
    st.code(st.session_state.last_status, language="text")
    
    time.sleep(1)
    st.rerun()
else:
    st.write("Bot is currently stopped. Enter credentials and click **Start Scanner** to begin.")
