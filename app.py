# AQ.Ab8RN6IzwsuciGIjST8209oOSuzeLGoH781sg4TesZvVGxLevA


import streamlit as st
import streamlit.components.v1 as components
import json
from PIL import Image
from google import genai
from datetime import datetime, timedelta

# 1. Initialize the Gemini Client
client = genai.Client(api_key="AQ.Ab8RN6KD-ntRbySz0N6Occomp8170th8g3PxK64pjreBuOeC5Q")

# 2. Configure the Streamlit Page
st.set_page_config(page_title="Ultra-Fast Terminal", layout="wide", initial_sidebar_state="collapsed")

# 3. CSS Styling (Including a hack to clean up the Uploader Box)
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #8B9BB4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    h1, h2, h3, h4 { color: #E2E8F0; margin-bottom: 5px; }
    
    /* CLEAN UP THE UPLOADER UI TO LOOK LIKE A PASTE BOX */
    [data-testid="stFileUploadDropzone"] > div > div > span { display: none; }
    [data-testid="stFileUploadDropzone"] > div > div::before { 
        content: "CLICK HERE AND PRESS CTRL+V TO PASTE CHART"; 
        color: #00FF99; 
        font-weight: bold; 
        font-size: 16px;
    }
    [data-testid="stFileUploadDropzone"] button { display: none; }
    
    /* Top Signal Box */
    .signal-box { background-color: #121620; border: 1px solid #E63946; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 15px;}
    .signal-put { color: #FF3366; font-size: 48px; font-weight: bold; text-shadow: 0 0 10px rgba(255,51,102,0.5); }
    .signal-call { color: #00FF99; font-size: 48px; font-weight: bold; text-shadow: 0 0 10px rgba(0,255,153,0.5); }
    
    /* 6-Grid Metrics */
    .metric-card { background-color: #121620; border: 1px solid #1E293B; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 10px; font-size: 11px; font-weight: bold; color: #64748b; text-transform: uppercase; }
    .metric-val-orange { color: #FFB703; font-size: 16px; margin-top: 5px; display: block; }
    .metric-val-cyan { color: #00e5ff; font-size: 16px; margin-top: 5px; display: block; }
    .metric-val-purple { color: #a855f7; font-size: 16px; margin-top: 5px; display: block; }
    
    /* Analysis Breakdown Rows */
    .analysis-row { display: flex; justify-content: space-between; border-bottom: 1px solid #1E293B; padding: 8px 0; font-size: 13px; }
    .analysis-val { color: #E2E8F0; }
    
    /* Structure Event Box */
    .choch-box { background-color: #1a0b2e; border: 1px solid #4a148c; border-radius: 8px; padding: 15px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;}
    .choch-badge { background-color: #6a1b9a; color: white; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 15px;}
    .choch-text { color: #E2E8F0; font-size: 14px; flex-grow: 1; }
    .choch-price { color: #00e5ff; font-weight: bold; font-size: 14px; }
    
    /* Section Headers */
    .section-header { display: flex; align-items: center; margin-top: 25px; margin-bottom: 15px; color: #00e5ff; font-weight: 600; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }
    .section-line { flex-grow: 1; height: 1px; background-color: #1E293B; margin-left: 15px; }

    /* Custom Progress Bars Container */
    .bar-row { display: flex; align-items: center; margin-bottom: 10px; background-color: transparent; border: 1px solid #1E293B; padding: 8px; border-radius: 6px;}
    .bar-label-box { width: 120px; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 12px; text-align: center; font-weight: bold; display: flex; align-items: center; justify-content: center;}
    .bar-label-red { color: #FF3366; background-color: rgba(255, 51, 102, 0.1); }
    .bar-label-green { color: #00FF99; background-color: rgba(0, 255, 153, 0.1); }
    .bar-label-blue { color: #60a5fa; background-color: rgba(96, 165, 250, 0.1); }
    .c-label { width: 80px; font-size: 12px; color: #64748b; }
    .pressure-label { width: 160px; font-size: 12px; color: #94a3b8; font-weight: bold; text-transform: uppercase; }
    
    /* The actual bars */
    .bar-track { flex-grow: 1; height: 4px; background-color: #1e293b; border-radius: 2px; margin: 0 15px; overflow: hidden;}
    .bar-fill { height: 100%; border-radius: 2px; }
    .bar-fill-red { background-color: #FF3366; box-shadow: 0 0 5px #FF3366;}
    .bar-fill-green { background-color: #00FF99; box-shadow: 0 0 5px #00FF99;}
    .bar-fill-blue { background-color: #3b82f6; box-shadow: 0 0 5px #3b82f6;}
    .bar-fill-purple { background-color: #a855f7; box-shadow: 0 0 5px #a855f7;}
    
    .bar-value { width: 40px; font-size: 14px; font-weight: bold; text-align: right; }
    .val-red { color: #FF3366; }
    .val-green { color: #00FF99; }
    .val-blue { color: #60a5fa; }
    .val-purple { color: #a855f7; }
    .val-neutral { color: #94a3b8; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Ultra-Fast Paste Terminal")

# Live Ticking Clock
clock_html = """
<div style="padding: 10px; background-color: #121620; border-radius: 8px; border: 1px solid #1E293B; color: #8B9BB4; font-size: 14px; margin-bottom:15px;">
    <div style="display: flex; justify-content: space-between;">
        <span>SYS CLOCK: <strong id="current-time" style="color: #E2E8F0;">--:--:--</strong></span>
        <span>ENTRY (NEXT CANDLE): <strong id="entry-time" style="color: #00FF99;">--:--:--</strong></span>
        <span>EXPIRY (+1 MIN): <strong id="target-time" style="color: #FFB703;">--:--:--</strong></span>
    </div>
</div>
<script>
    function updateClock() {
        const now = new Date();
        const nextMinute = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes() + 1, 0, 0);
        const expiry = new Date(nextMinute.getTime() + 60000);
        
        document.getElementById('current-time').innerText = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        document.getElementById('entry-time').innerText = nextMinute.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        document.getElementById('target-time').innerText = expiry.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    }
    setInterval(updateClock, 1000); updateClock(); 
</script>
"""
components.html(clock_html, height=50)

# Helper functions for UI
def custom_bar(label_col1, label_col2, color_class, percentage, label_col2_class=""):
    fill_class = f"bar-fill-{color_class}"
    val_class = f"val-{color_class}" if color_class else "val-neutral"
    return f"""
    <div class="bar-row" style="border:none; padding: 5px 0;">
        <div class="c-label {label_col2_class}">{label_col1}</div>
        <div class="bar-track"><div class="bar-fill {fill_class}" style="width: {percentage}%;"></div></div>
        <div class="bar-value {val_class}">{percentage}%</div>
    </div>
    """

def custom_candle_bar(c_index, name, color_class, percentage, icon=""):
    fill_class = f"bar-fill-{color_class}"
    box_class = f"bar-label-{color_class}" if color_class != 'blue' else "bar-label-blue"
    return f"""
    <div class="bar-row">
        <div class="c-label">{c_index}</div>
        <div class="bar-label-box {box_class}">{icon} {name}</div>
        <div class="bar-track"><div class="bar-fill {fill_class}" style="width: {percentage}%;"></div></div>
        <div class="bar-value val-neutral">{percentage}%</div>
    </div>
    """

uploaded_files = st.file_uploader("Upload", type=["png", "jpg", "jpeg"], label_visibility="collapsed")

if uploaded_files:
    # 1. Display the raw image to the user instantly
    img = Image.open(uploaded_files)
    st.image(img, use_container_width=True)
    st.markdown("---")
    
    if st.button("🚀 EXECUTE FAST ANALYSIS", use_container_width=True, type="primary"):
        with st.spinner("Compressing image & processing technicals..."):
            try:
                # 2. PILLOW COMPRESSION: Shrink the image to slash upload time
                fast_img = img.copy()
                if fast_img.mode in ("RGBA", "P"):
                    fast_img = fast_img.convert("RGB")
                
                # Resize keeping aspect ratio (max 800x800). This drops the size from MBs to KBs.
                fast_img.thumbnail((800, 800)) 
                
                now = datetime.now()
                next_candle_start = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                entry_time_str = next_candle_start.strftime("%H:%M")
                
                prompt = """
                You are an expert algorithmic trading system. Analyze the 1-minute chart.
                Return ONLY a raw JSON object formatted EXACTLY like this (replace with analyzed values):
                {
                    "asset": "OTC_ASSET",
                    "signal_direction": "PUT",
                    "current_price": "0.0000",
                    "trend": "BEARISH",
                    "confidence": "LOW",
                    "trend_type": "UPTREND",
                    "signal_strength": 62,
                    "market_pressure_split": {"put": 62, "call": 38},
                    "support": "0.19957",
                    "resistance": "0.20054",
                    "payout": "94%",
                    "analysis": {
                        "ema_alignment": "Bearish Stack",
                        "rsi": "58.7 Neutral",
                        "macd": "Negative",
                        "market_structure": "UPTREND",
                        "candle_momentum": "Strong Bearish",
                        "rejection_candle": "None",
                        "volume_breakout": "No",
                        "volatility": "0.14%",
                        "price_vs_bb": "Inside Band",
                        "pullback": "Minimal",
                        "support_prox": "44pips",
                        "resistance_prox": "3pips",
                        "bos": "None",
                        "choch": "Bear Reversal"
                    },
                    "structure_event": {
                        "type": "CHOCH ↓",
                        "desc": "Character changed — prior structure broken.",
                        "price": "0.20076"
                    },
                    "candles": [
                        {"id": "C0 (Latest)", "name": "Weak Bear", "type": "red", "val": 50, "icon": "▽"},
                        {"id": "C1", "name": "Hang. Man", "type": "red", "val": 21, "icon": "🔨"},
                        {"id": "C2", "name": "Weak Bear", "type": "red", "val": 53, "icon": "▽"},
                        {"id": "C3", "name": "Bull Marubozu", "type": "green", "val": 96, "icon": "🟩"},
                        {"id": "C4", "name": "Bull Engulf", "type": "green", "val": 47, "icon": "🟩"},
                        {"id": "C5", "name": "Spinning Top", "type": "blue", "val": 21, "icon": "🌀"}
                    ],
                    "pressure": {
                        "bull_body": 45, "bear_body": 55, "volume": 33,
                        "momentum": 50, "bull_wick": 74, "bear_wick": 19,
                        "overall_summary": "Overall pressure: BEARISH - Body dominance: 55%"
                    }
                }
                """
                
                # Send the tiny, compressed image (`fast_img`) instead of the massive original
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=[prompt, fast_img]
                )
                
                raw_response = response.text.strip()
                if raw_response.startswith("```json"): raw_response = raw_response[7:-3].strip()
                elif raw_response.startswith("```"): raw_response = raw_response[3:-3].strip()
                data = json.loads(raw_response)
                
                # --- RENDER UI ---
                col1, col2 = st.columns([1.2, 1])
                
                with col1:
                    st.markdown(f"### 🎯 {data.get('asset', 'ASSET')}")
                    
                    direction = data.get('signal_direction', 'PUT')
                    sig_class = "signal-call" if direction == "CALL" else "signal-put"
                    arrow = "▲" if direction == "CALL" else "▼"
                    st.markdown(f'<div class="signal-box"><div class="{sig_class}">{arrow}<br>{direction}</div></div>', unsafe_allow_html=True)
                    
                    g1, g2, g3 = st.columns(3)
                    g1.markdown(f"<div class='metric-card'>TREND<span class='metric-val-orange'>{data.get('trend', '-')}</span></div>", unsafe_allow_html=True)
                    g2.markdown(f"<div class='metric-card'>NEXT ENTRY<span class='metric-val-cyan'>{entry_time_str}</span></div>", unsafe_allow_html=True)
                    g3.markdown(f"<div class='metric-card'>CURRENT PRICE<span class='metric-val-purple'>{data.get('current_price', '-')}</span></div>", unsafe_allow_html=True)
                    
                    g4, g5, g6 = st.columns(3)
                    g4.markdown(f"<div class='metric-card'>CONFIDENCE<span class='metric-val-orange'>{data.get('confidence', '-')}</span></div>", unsafe_allow_html=True)
                    g5.markdown(f"<div class='metric-card'>EXPIRY<span class='metric-val-cyan'>1 MIN</span></div>", unsafe_allow_html=True)
                    g6.markdown(f"<div class='metric-card'>TREND TYPE<span class='metric-val-cyan'>{data.get('trend_type', '-')}</span></div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div style='color:#64748b; font-size:12px; font-weight:bold; margin-top:10px;'>SIGNAL STRENGTH <span style='float:right; color:#00FF99; font-size:16px;'>{data.get('signal_strength', 50)}%</span></div>", unsafe_allow_html=True)
                    st.progress(data.get('signal_strength', 50) / 100.0)
                    
                    put_p = data.get('market_pressure_split', {}).get('put', 50)
                    call_p = data.get('market_pressure_split', {}).get('call', 50)
                    st.markdown(f"""
                        <div style="display:flex; width:100%; height:24px; border-radius:4px; overflow:hidden; margin-top:15px; margin-bottom:15px;">
                            <div style="width:{put_p}%; background-color:#FF3366; text-align:left; font-size:12px; color:white; padding: 4px 10px; font-weight:bold;">PUT {put_p}%</div>
                            <div style="width:{call_p}%; background-color:#00FF99; text-align:right; font-size:12px; color:#121620; padding: 4px 10px; font-weight:bold;">CALL {call_p}%</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    sr1, sr2 = st.columns(2)
                    sr1.markdown(f"<div class='metric-card' style='border-color:#4a0f1d;'>RESISTANCE<span class='metric-val-cyan' style='color:#FF3366;'>{data.get('resistance', '-')}</span></div>", unsafe_allow_html=True)
                    sr2.markdown(f"<div class='metric-card' style='border-color:#063b27;'>SUPPORT<span class='metric-val-cyan' style='color:#00FF99;'>{data.get('support', '-')}</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='metric-card' style='border-color:#4a148c; text-align:left; display:flex; justify-content:space-between; align-items:center;'><div>PAYOUT<br><span style='font-size:10px; font-weight:normal;'>Platform return</span></div><span class='metric-val-purple' style='font-size:24px; margin:0;'>{data.get('payout', '-')}</span></div>", unsafe_allow_html=True)
                    
                with col2:
                    st.markdown("""<div class="section-header" style="margin-top:0;"><span class="section-icon">🔬</span> ANALYSIS BREAKDOWN <div class="section-line"></div></div>""", unsafe_allow_html=True)
                    ana = data.get('analysis', {})
                    for key, val in ana.items():
                        formatted_key = key.replace('_', ' ').title()
                        val_class = "val-red" if "Bear" in str(val) or "Negative" in str(val) else "val-green" if "Bull" in str(val) or "UPTREND" in str(val) else "analysis-val"
                        st.markdown(f"<div class='analysis-row'><span>{formatted_key}</span><span class='{val_class}'>{val}</span></div>", unsafe_allow_html=True)
                
                st.markdown("""<div class="section-header"><span class="section-icon">🧱</span> STRUCTURE EVENTS <div class="section-line"></div></div>""", unsafe_allow_html=True)
                evt = data.get('structure_event', {})
                st.markdown(f"""
                <div class="choch-box">
                    <div class="choch-badge">{evt.get('type', 'CHOCH')}</div>
                    <div class="choch-text">{evt.get('desc', 'Structure shift detected.')}</div>
                    <div class="choch-price">{evt.get('price', '0.000')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("""<div class="section-header"><span class="section-icon">🕯️</span> CANDLE MOVEMENT <div class="section-line"></div></div>""", unsafe_allow_html=True)
                for c in data.get('candles', []):
                    st.markdown(custom_candle_bar(c.get('id'), c.get('name'), c.get('type'), c.get('val'), c.get('icon')), unsafe_allow_html=True)
                
                st.markdown("""<div class="section-header"><span class="section-icon">📊</span> MARKET PRESSURE <div class="section-line"></div></div>""", unsafe_allow_html=True)
                pres = data.get('pressure', {})
                html_pres = custom_bar("BULL BODY PRESS.", "", "green", pres.get('bull_body', 0), "pressure-label")
                html_pres += custom_bar("BEAR BODY PRESS.", "", "red", pres.get('bear_body', 0), "pressure-label")
                html_pres += custom_bar("VOLUME PRESSURE", "", "blue", pres.get('volume', 0), "pressure-label")
                html_pres += custom_bar("MOMENTUM (EMA)", "", "purple", pres.get('momentum', 0), "pressure-label")
                html_pres += custom_bar("BULL WICK REJECT.", "", "green", pres.get('bull_wick', 0), "pressure-label")
                html_pres += custom_bar("BEAR WICK REJECT.", "", "red", pres.get('bear_wick', 0), "pressure-label")
                st.markdown(html_pres, unsafe_allow_html=True)
                
                st.markdown(f"<div style='border: 1px solid #1e293b; border-radius: 8px; padding: 15px; margin-top: 10px; font-size: 13px; color: #e2e8f0;'><strong>{pres.get('overall_summary', '')}</strong></div>", unsafe_allow_html=True)

            except json.JSONDecodeError:
                st.error("JSON Error.")
                st.code(raw_response)
            except Exception as e:
                st.error(f"Error: {e}")
