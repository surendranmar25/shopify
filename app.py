"""
app.py — ShopSync main entry point.

File layout
───────────────────────────────────────────────
app.py              ← you are here (UI shell, sidebar, tabs)
price_update.py     ← 🏷️  Price Update tab logic
stock_update.py     ← 📦  Stock Update tab logic
shopify_api.py      ← backend helpers (API calls, file parsing, Google Sheets)
───────────────────────────────────────────────
"""

import json
import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

# ── Local modules ─────────────────────────────────────────────────────────────
from shopify_api import (
    load_config,
    save_config,
    fetch_all_shopify_skus,
    fetch_google_sheet_public,
    fetch_google_sheet_private,
    process_price_file,
    process_stock_file,
    get_shopify_location_id,
    update_variant_price,
    set_inventory_level,
    excel_download,
)
import price_update   # renders the 🏷️ Price Update tab
import stock_update   # renders the 📦 Stock Update tab

# ============================================================
# PAGE CONFIG  (must be the very first Streamlit call)
# ============================================================
st.set_page_config(
    page_title="ShopSync — Shopify Bulk Updater",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# GLOBAL CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --shopify-green:  #008060;
    --shopify-green2: #004c3f;
    --accent:         #5c6ac4;
    --card-bg:        #ffffff;
    --border:         #e1e3e5;
    --text-main:      #202223;
    --text-muted:     #6d7175;
    --success:        #008060;
    --warning:        #ffc453;
    --danger:         #d82c0d;
    --radius:         12px;
    --shadow:         0 2px 12px rgba(0,0,0,0.07);
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: var(--text-main); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--shopify-green2) 0%, #006b50 100%);
}
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #fff !important; border-radius: 8px;
}
[data-testid="stSidebar"] .stTextInput input::placeholder { color: rgba(255,255,255,0.55) !important; }
[data-testid="stSidebar"] label { color: rgba(255,255,255,0.85) !important; font-size: 0.82rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #f0f0f0; padding: 5px; border-radius: 10px; border-bottom: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 0.55rem 1.6rem; font-weight: 500;
    font-size: 0.92rem; background: transparent; border: none;
    color: var(--text-muted); transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: #fff !important; color: var(--shopify-green) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* ── Cards ── */
.card {
    background: var(--card-bg); border-radius: var(--radius);
    border: 1px solid var(--border); padding: 1.4rem 1.6rem;
    box-shadow: var(--shadow); margin-bottom: 1.2rem;
}

/* ── Metric cards ── */
.metric-card {
    flex: 1; min-width: 140px; background: var(--card-bg);
    border-radius: var(--radius); border: 1px solid var(--border);
    padding: 1.1rem 1.3rem; box-shadow: var(--shadow); text-align: center;
}
.metric-card .m-icon  { font-size: 1.7rem; margin-bottom: 0.3rem; }
.metric-card .m-value { font-size: 1.75rem; font-weight: 700; color: var(--shopify-green); }
.metric-card .m-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.1rem; }

/* ── Badges ── */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
.badge-success { background: #e3f5ef; color: var(--success); }
.badge-warning { background: #fff3cd; color: #7a5100; }
.badge-danger  { background: #fce8e6; color: var(--danger); }
.badge-info    { background: #edf0ff; color: var(--accent); }
.badge-gs      { background: #e8f5e9; color: #2e7d32; }

/* ── Section headers ── */
.section-header {
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 1.05rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.8rem;
}
.section-header .dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--shopify-green); display: inline-block;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border) !important; border-radius: var(--radius) !important;
    background: #fafafa !important; padding: 0.8rem !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--shopify-green) !important; background: #f0faf6 !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--shopify-green) 0%, #005c45 100%);
    color: #fff; border: none; border-radius: 8px; padding: 0.55rem 1.8rem;
    font-weight: 600; font-size: 0.9rem; letter-spacing: 0.02em;
    transition: all 0.25s; box-shadow: 0 2px 8px rgba(0,128,96,0.3);
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,128,96,0.4); }
.stButton > button:active { transform: translateY(0); }

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: #fff !important; color: var(--shopify-green) !important;
    border: 2px solid var(--shopify-green) !important; border-radius: 8px !important; font-weight: 600 !important;
}
[data-testid="stDownloadButton"] > button:hover { background: #f0faf6 !important; }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, var(--shopify-green), #00a47a) !important; border-radius: 99px !important;
}

/* ── Log area ── */
.log-container {
    background: #1a1a2e; border-radius: 8px; padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace; font-size: 0.82rem; color: #a8ff78;
    max-height: 260px; overflow-y: auto; line-height: 1.7;
}

/* ── Steps ── */
.steps { display: flex; gap: 0; margin-bottom: 1.2rem; }
.step {
    flex: 1; text-align: center; padding: 0.5rem 0.3rem;
    font-size: 0.78rem; font-weight: 500;
    border-top: 3px solid var(--border); color: var(--text-muted);
}
.step.active { border-top-color: var(--shopify-green); color: var(--shopify-green); }
.step.done   { border-top-color: var(--shopify-green); color: var(--text-muted); }

/* ── Info / warning boxes ── */
.info-box {
    background: #edf2ff; border-left: 4px solid var(--accent);
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #2c3e9e; margin-bottom: 1rem;
}
.info-box strong { display: block; margin-bottom: 0.2rem; }
.warning-box {
    background: #fff8ee; border-left: 4px solid #ffc453;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #7a5100; margin-bottom: 1rem;
}
.gs-box {
    background: #e8f5e9; border-left: 4px solid #4caf50;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    font-size: 0.85rem; color: #1b5e20; margin-bottom: 1rem;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
    background: var(--card-bg) !important; box-shadow: var(--shadow) !important; margin-bottom: 1.2rem !important;
}
[data-testid="stExpander"] summary { font-weight: 600 !important; font-size: 0.92rem !important; }

/* ── Page header ── */
.page-header {
    background: linear-gradient(135deg, var(--shopify-green2) 0%, #006b50 100%);
    border-radius: var(--radius); padding: 1.6rem 2rem; margin-bottom: 1.6rem;
    color: #fff; display: flex; align-items: center; justify-content: space-between;
}
.page-header h1 { font-size: 1.55rem; font-weight: 700; margin: 0; }
.page-header p  { font-size: 0.87rem; opacity: 0.8; margin: 0.25rem 0 0; }
.page-header .header-icon { font-size: 2.6rem; }

/* ── Sidebar logo ── */
.sidebar-logo {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.2rem 0 1.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.2); margin-bottom: 1.2rem;
}
.sidebar-logo .logo-icon { font-size: 2rem; }
.sidebar-logo .logo-text { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.01em; }
.sidebar-logo .logo-sub  { font-size: 0.72rem; opacity: 0.65; margin-top: -2px; }

/* ── Connection pill ── */
.conn-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.13); border: 1px solid rgba(255,255,255,0.22);
    border-radius: 20px; padding: 5px 14px; font-size: 0.78rem; font-weight: 500;
}
.conn-pill .dot-live {
    width: 8px; height: 8px; border-radius: 50%; background: #3dca8a;
    box-shadow: 0 0 0 3px rgba(61,202,138,0.3); animation: pulse 1.8s infinite;
}
.conn-pill .dot-off { width: 8px; height: 8px; border-radius: 50%; background: #ff7b7b; }
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(61,202,138,0.3); }
    50%       { box-shadow: 0 0 0 6px rgba(61,202,138,0.1); }
}

/* ── Auto-sync status box ── */
.autosync-box {
    background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
    border-radius: 10px; padding: 10px 14px; margin-top: 8px;
    font-size: 0.8rem; line-height: 1.9;
}
.autosync-active { border-left: 3px solid #3dca8a; }
.countdown { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.05em; }

hr { border-color: var(--border); margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION STATE INIT  (runs once per browser session)
# ============================================================
if "config_loaded" not in st.session_state:
    cfg    = load_config()
    as_cfg = cfg.get("auto_sync", {})

    st.session_state.saved_shop_url     = cfg.get("shop_url", "")
    st.session_state.saved_token        = cfg.get("access_token", "")
    st.session_state.saved_api_version  = cfg.get("api_version", "2025-04")

    # Auto-sync settings
    st.session_state.auto_sync_enabled  = as_cfg.get("enabled", False)
    st.session_state.auto_sync_interval = as_cfg.get("interval_seconds", 1800)
    st.session_state.auto_sync_type     = as_cfg.get("sync_type", "Price Only")
    st.session_state.gs_url             = as_cfg.get("sheet_url", "")
    st.session_state.gs_auth_type       = as_cfg.get("auth_type", "public")
    st.session_state.gs_sheet_name      = as_cfg.get("sheet_name", "Sheet1")

    # Runtime state
    st.session_state.next_sync_time     = None
    st.session_state.last_sync_time     = None
    st.session_state.last_sync_results  = None
    st.session_state.gs_service_account = None

    st.session_state.config_loaded = True


# ============================================================
# CACHED SKU FETCHER  (shared across tabs, refreshes every 5 min)
# ============================================================
@st.cache_data(ttl=300, show_spinner=False)
def _cached_skus(shop_url, api_version, access_token):
    return fetch_all_shopify_skus(shop_url, api_version, access_token)


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-icon">🛍️</div>
        <div>
            <div class="logo-text">ShopSync</div>
            <div class="logo-sub">Shopify Bulk Updater</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### ⚙️ API Configuration")
    sb_url     = st.text_input("Shop URL",     value=st.session_state.saved_shop_url,
                                placeholder="yourstore.myshopify.com", key="sidebar_shop_url")
    sb_token   = st.text_input("Access Token", value=st.session_state.saved_token,
                                placeholder="shpat_xxxxxxxxxxxx", type="password", key="sidebar_token")
    sb_version = st.text_input("API Version",  value=st.session_state.saved_api_version,
                                key="sidebar_api_version")

    if st.button("💾 Save API Settings", use_container_width=True, key="sb_save"):
        cfg = load_config()
        cfg.update(shop_url=sb_url, access_token=sb_token, api_version=sb_version)
        save_config(cfg)
        st.session_state.saved_shop_url    = sb_url
        st.session_state.saved_token       = sb_token
        st.session_state.saved_api_version = sb_version
        st.success("✅ Saved!")

    st.markdown("---")

    # Connection pill
    if sb_url and sb_token:
        st.markdown('<div class="conn-pill"><span class="dot-live"></span> Connected</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="conn-pill"><span class="dot-off"></span> Not connected</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    # Auto-sync countdown
    if st.session_state.auto_sync_enabled and st.session_state.next_sync_time:
        rem  = max(0, int(st.session_state.next_sync_time - time.time()))
        mins, secs = divmod(rem, 60)
        hrs,  mins = divmod(mins, 60)
        cd   = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
        last = ""
        if st.session_state.last_sync_time:
            last = f"<br>🕑 Last: {datetime.fromtimestamp(st.session_state.last_sync_time).strftime('%H:%M:%S')}"
        st.markdown(f"""
        <div class="autosync-box autosync-active">
            🔄 <strong>Auto-Sync ON</strong><br>
            ⏱️ Next: <span class="countdown">{cd}</span>{last}
        </div>""", unsafe_allow_html=True)
    elif st.session_state.auto_sync_enabled:
        st.markdown("""
        <div class="autosync-box autosync-active">
            🔄 <strong>Auto-Sync ON</strong><br>
            Open 📊 Google Sheets tab → Start Auto-Sync
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; opacity:0.7; line-height:1.8;">
    <strong style="opacity:1;">📋 Quick Guide</strong><br>
    1. Enter &amp; <strong>Save</strong> API credentials<br>
    2. 🏷️ Price tab → upload price file<br>
    3. 📦 Stock tab → upload stock file<br>
    4. 📊 Google Sheets → auto-sync setup<br>
    5. Download the result report
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; opacity:0.55; text-align:center;">
    ShopSync v2.0 · Built for Shopify
    </div>""", unsafe_allow_html=True)


# ============================================================
# RESOLVE FINAL CREDENTIALS
# ============================================================
SHOP_URL     = st.session_state.get("sidebar_shop_url", "")
ACCESS_TOKEN = st.session_state.get("sidebar_token", "")
API_VERSION  = st.session_state.get("sidebar_api_version", "") or "2025-04"

# ── Inline API panel (always visible even if sidebar is collapsed) ────────────
connected  = bool(SHOP_URL and ACCESS_TOKEN)
exp_label  = ("⚙️ API Settings  ·  ✅ Connected" if connected
               else "⚙️ API Settings  ·  ⚠️ Not configured — click to set up")

with st.expander(exp_label, expanded=not connected):
    ec1, ec2, ec3, save_col = st.columns([3, 3, 2, 1])
    with ec1:
        il_url = st.text_input("🌐 Shop URL", value=SHOP_URL,
                                placeholder="yourstore.myshopify.com", key="inline_shop_url")
    with ec2:
        il_tok = st.text_input("🔑 Access Token", value=ACCESS_TOKEN,
                                placeholder="shpat_xxxxxxxxxxxx", type="password", key="inline_token")
    with ec3:
        il_ver = st.text_input("📅 API Version", value=API_VERSION, key="inline_api_version")
    with save_col:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Save", key="inline_save", use_container_width=True):
            cfg = load_config()
            cfg.update(shop_url=il_url, access_token=il_tok, api_version=il_ver)
            save_config(cfg)
            st.session_state.saved_shop_url    = il_url
            st.session_state.saved_token       = il_tok
            st.session_state.saved_api_version = il_ver
            st.success("✅ Saved!")

    if il_url and il_tok:
        st.markdown('<span class="badge badge-success">✅ Credentials entered — collapse this panel</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-warning">⚠️ Fill in Shop URL and Access Token</span>',
                    unsafe_allow_html=True)

# Merge: inline overrides sidebar
SHOP_URL     = il_url     or SHOP_URL
ACCESS_TOKEN = il_tok     or ACCESS_TOKEN
API_VERSION  = il_ver     or API_VERSION or "2025-04"


# ============================================================
# PAGE HEADER
# ============================================================
st.markdown("""
<div class="page-header">
    <div>
        <h1>🛍️ ShopSync — Shopify Bulk Updater</h1>
        <p>Sync prices and inventory from your ERP or Google Sheets directly into Shopify</p>
    </div>
    <div class="header-icon">📦</div>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SUMMARY METRICS
# ============================================================
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""<div class="metric-card">
        <div class="m-icon">🏷️</div><div class="m-value">—</div>
        <div class="m-label">Prices Updated</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""<div class="metric-card">
        <div class="m-icon">📦</div><div class="m-value">—</div>
        <div class="m-label">Stock Updated</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""<div class="metric-card">
        <div class="m-icon">✅</div><div class="m-value">—</div>
        <div class="m-label">SKUs Matched</div></div>""", unsafe_allow_html=True)
with c4:
    last_run = "—"
    if st.session_state.last_sync_time:
        last_run = datetime.fromtimestamp(st.session_state.last_sync_time).strftime("%H:%M")
    st.markdown(f"""<div class="metric-card">
        <div class="m-icon">⏱️</div><div class="m-value">{last_run}</div>
        <div class="m-label">Last Run</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ============================================================
# FILE UPLOADERS  (above tabs — always visible)
# ============================================================
up1, up2 = st.columns(2)

with up1:
    st.markdown("""<div class="section-header">
        <span class="dot" style="background:#5c6ac4;"></span>Price Update File
    </div>""", unsafe_allow_html=True)
    price_file = st.file_uploader("Price CSV / Excel", type=["csv", "xlsx", "xls"],
                                   key="price_file", label_visibility="collapsed")
    st.markdown("""<div class="info-box">
        <strong>Required columns</strong>
        <code>ERP Code</code> &nbsp;|&nbsp; <code>Display Price</code>
    </div>""", unsafe_allow_html=True)

with up2:
    st.markdown("""<div class="section-header">
        <span class="dot"></span>Stock Update File
    </div>""", unsafe_allow_html=True)
    stock_file = st.file_uploader("Stock CSV / Excel", type=["csv", "xlsx", "xls"],
                                   key="stock_file", label_visibility="collapsed")
    st.markdown("""<div class="info-box" style="background:#edf8f4;border-left-color:#008060;color:#004c3f;">
        <strong>Required columns</strong>
        <code>ERP Code</code> &nbsp;|&nbsp; <code>Stock Quantity</code>
    </div>""", unsafe_allow_html=True)

st.markdown("---")


# ============================================================
# TABS
# ============================================================
tab_price, tab_stock, tab_gs, tab_guide = st.tabs([
    "🏷️  Price Update",
    "📦  Stock Update",
    "📊  Google Sheets Sync",
    "📖  How to Use",
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — delegate to price_update.py
# ─────────────────────────────────────────────────────────────
with tab_price:
    price_update.render(
        price_file=price_file,
        shop_url=SHOP_URL,
        api_version=API_VERSION,
        access_token=ACCESS_TOKEN,
        get_skus_fn=_cached_skus,
    )

# ─────────────────────────────────────────────────────────────
# TAB 2 — delegate to stock_update.py
# ─────────────────────────────────────────────────────────────
with tab_stock:
    stock_update.render(
        stock_file=stock_file,
        shop_url=SHOP_URL,
        api_version=API_VERSION,
        access_token=ACCESS_TOKEN,
        get_skus_fn=_cached_skus,
    )

# ─────────────────────────────────────────────────────────────
# TAB 3 — GOOGLE SHEETS SYNC
# ─────────────────────────────────────────────────────────────
with tab_gs:
    st.markdown("""
    <div class="section-header" style="font-size:1.15rem; margin-top:0.5rem;">
        <span class="dot" style="background:#34a853;"></span>
        Google Sheets Auto-Sync
        &nbsp;<span class="badge badge-gs">🔄 Auto-Sync</span>
    </div>
    <div class="gs-box">
        <strong>How it works</strong>
        Update your Google Sheet → ShopSync reads it every N minutes →
        Shopify prices &amp; stock update automatically. No manual uploads needed!
    </div>""", unsafe_allow_html=True)

    # ── Sheet URL & auth ──────────────────────────────────────
    gs_col1, gs_col2 = st.columns([3, 1])
    with gs_col1:
        gs_url_input = st.text_input(
            "📋 Google Sheet URL",
            value=st.session_state.gs_url,
            placeholder="https://docs.google.com/spreadsheets/d/...",
            key="gs_url_input",
        )
    with gs_col2:
        gs_auth_type = st.radio(
            "Sheet Access",
            ["Public", "Private (Service Account)"],
            index=0 if st.session_state.gs_auth_type == "public" else 1,
            key="gs_auth_radio",
        )

    service_account_info = st.session_state.gs_service_account
    gs_sheet_name = "Sheet1"

    if gs_auth_type == "Private (Service Account)":
        gs_sheet_name = st.text_input("Sheet / Tab Name",
                                       value=st.session_state.gs_sheet_name,
                                       placeholder="Sheet1", key="gs_sheet_name_input")
        sa_file = st.file_uploader("Upload Service Account JSON",
                                    type=["json"], key="gs_sa_file")
        if sa_file:
            try:
                service_account_info = json.load(sa_file)
                st.session_state.gs_service_account = service_account_info
                st.success("✅ Service account loaded")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
        elif service_account_info:
            st.markdown('<span class="badge badge-success">✅ Service account in memory</span>',
                        unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge badge-warning">⚠️ Upload your service account JSON</span>',
                        unsafe_allow_html=True)

    # ── Sync type ─────────────────────────────────────────────
    st.markdown("##### 🔧 Sync Options")
    sync_type = st.radio(
        "What to sync from this sheet",
        ["Price Only", "Stock Only", "Both Price & Stock"],
        horizontal=True, key="gs_sync_type",
    )

    st.markdown("""<div class="info-box">
        <strong>Required Google Sheet columns</strong>
        <code>ERP Code</code> — your SKU &nbsp;|&nbsp;
        <code>Display Price</code> — for price sync &nbsp;|&nbsp;
        <code>Stock Quantity</code> — for stock sync
    </div>""", unsafe_allow_html=True)

    # Sample template download
    def _gs_template() -> BytesIO:
        df = pd.DataFrame({
            "ERP Code":       ["LAPTOP001", "MOUSE002", "KB003", "MON004", "CHAIR005"],
            "Display Price":  [54999, 1299, 2499, 18999, 9999],
            "Stock Quantity": [25, 150, 80, 40, 60],
        })
        buf = BytesIO(); df.to_excel(buf, index=False, engine="openpyxl"); buf.seek(0)
        return buf

    st.download_button(
        "📥 Download Google Sheet Template",
        data=_gs_template(),
        file_name="sample_google_sheet_template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_gs_template",
    )

    st.markdown("---")

    # ── Helper: fetch sheet data ──────────────────────────────
    def _fetch_gs():
        if gs_auth_type == "Private (Service Account)":
            if not service_account_info:
                return None, "Upload your service account JSON first."
            import re
            m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", gs_url_input)
            if not m:
                return None, "Invalid Google Sheet URL."
            return fetch_google_sheet_private(service_account_info, m.group(1), gs_sheet_name)
        return fetch_google_sheet_public(gs_url_input)

    # ── Helper: run sync from a dataframe ────────────────────
    def _do_sync(df_data: pd.DataFrame, label: str = "Sync"):
        if not SHOP_URL or not ACCESS_TOKEN:
            st.error("⚠️ Enter Shopify API credentials first.")
            return

        with st.spinner(f"🔄 {label} — fetching Shopify products…"):
            shopify_skus, skuerr = _cached_skus(SHOP_URL, API_VERSION, ACCESS_TOKEN)
        if skuerr:
            st.error(skuerr); return

        price_res = stock_res = None
        mode = st.session_state.get("gs_sync_type", "Price Only")

        if mode in ["Price Only", "Both Price & Stock"]:
            sku_price, perr = process_price_file(df_data)
            if perr:
                st.warning(f"Price columns: {perr}")
            elif sku_price:
                matched_p = set(sku_price) & set(shopify_skus)
                up = sk = er = 0
                for sku in matched_p:
                    if shopify_skus[sku]["price"] == sku_price[sku]:
                        sk += 1; continue
                    r = update_variant_price(SHOP_URL, API_VERSION, ACCESS_TOKEN,
                                             shopify_skus[sku]["variant_id"], sku_price[sku])
                    if r.status_code == 200: up += 1
                    else: er += 1
                    time.sleep(0.2)
                price_res = {"matched": len(matched_p), "updated": up, "skipped": sk, "errors": er}

        if mode in ["Stock Only", "Both Price & Stock"]:
            sku_stock, serr = process_stock_file(df_data)
            if serr:
                st.warning(f"Stock columns: {serr}")
            elif sku_stock:
                with st.spinner("Fetching inventory location…"):
                    loc_id, locerr = get_shopify_location_id(SHOP_URL, API_VERSION, ACCESS_TOKEN)
                if locerr:
                    st.error(locerr)
                else:
                    matched_s = set(sku_stock) & set(shopify_skus)
                    up = er = 0
                    for sku in matched_s:
                        inv = shopify_skus[sku].get("inventory_item_id")
                        if not inv: er += 1; continue
                        r = set_inventory_level(SHOP_URL, API_VERSION, ACCESS_TOKEN,
                                                loc_id, inv, sku_stock[sku])
                        if r.status_code == 200: up += 1
                        else: er += 1
                        time.sleep(0.2)
                    stock_res = {"matched": len(matched_s), "updated": up, "errors": er}

        st.session_state.last_sync_time    = time.time()
        st.session_state.last_sync_results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "label": label, "price": price_res, "stock": stock_res,
        }

    # ── Preview / Manual sync buttons ────────────────────────
    pb, sb_btn, _ = st.columns([1, 1, 3])
    with pb:
        preview_btn = st.button("👁️ Preview Sheet",  key="gs_preview",      use_container_width=True)
    with sb_btn:
        manual_btn  = st.button("⚡ Sync Now",        key="gs_manual_sync",  use_container_width=True)

    if preview_btn:
        if not gs_url_input:
            st.warning("Enter a Google Sheet URL first.")
        else:
            with st.spinner("Fetching…"):
                df_gs, err = _fetch_gs()
            if err: st.error(err)
            else:
                st.markdown(f"**Preview** — {len(df_gs)} rows, {len(df_gs.columns)} cols")
                st.dataframe(df_gs.head(10), use_container_width=True, hide_index=True)

    if manual_btn:
        if not gs_url_input:
            st.warning("Enter a Google Sheet URL first.")
        else:
            with st.spinner("Fetching sheet data…"):
                df_gs, err = _fetch_gs()
            if err: st.error(err)
            else:
                _do_sync(df_gs, "Manual Sync")
                res = st.session_state.last_sync_results
                st.success(f"✅ Sync complete at {res['timestamp']}")
                if res.get("price"):
                    p = res["price"]
                    st.markdown(f"🏷️ **Price:** {p['matched']} matched → "
                                f"{p['updated']} updated, {p['skipped']} skipped, {p['errors']} errors")
                if res.get("stock"):
                    s = res["stock"]
                    st.markdown(f"📦 **Stock:** {s['matched']} matched → "
                                f"{s['updated']} updated, {s['errors']} errors")

    # Last sync results card
    if st.session_state.last_sync_results:
        res = st.session_state.last_sync_results
        with st.expander(f"📋 Last Sync — {res['timestamp']} ({res['label']})", expanded=False):
            if res.get("price"):
                p = res["price"]
                pc1, pc2, pc3, pc4 = st.columns(4)
                pc1.metric("Matched", p["matched"]); pc2.metric("Updated", p["updated"])
                pc3.metric("Skipped", p["skipped"]); pc4.metric("Errors",  p["errors"])
            if res.get("stock"):
                s = res["stock"]
                sc1, sc2, sc3 = st.columns(3)
                sc1.metric("Matched", s["matched"]); sc2.metric("Updated", s["updated"])
                sc3.metric("Errors",  s["errors"])

    st.markdown("---")

    # ── Auto-Sync Scheduler ───────────────────────────────────
    st.markdown("### 🔄 Auto-Sync Schedule")

    INTERVALS = {
        "5 minutes":  300,  "15 minutes": 900,  "30 minutes": 1800,
        "1 hour":     3600, "2 hours":    7200,  "4 hours":    14400,
        "Custom…":    None,
    }

    asc1, asc2 = st.columns([1, 2])
    with asc1:
        auto_toggle = st.toggle("Enable Auto-Sync",
                                 value=st.session_state.auto_sync_enabled,
                                 key="gs_auto_toggle")
    with asc2:
        interval_label = st.selectbox("Sync Interval", list(INTERVALS.keys()),
                                       index=2, key="gs_interval_sel")

    if interval_label == "Custom…":
        custom_mins    = st.number_input("Custom interval (minutes)", min_value=1,
                                          max_value=1440, value=30, key="gs_custom_mins")
        interval_secs  = custom_mins * 60
    else:
        interval_secs  = INTERVALS[interval_label]

    start_col, stop_col, _ = st.columns([1, 1, 3])
    with start_col:
        start_btn = st.button("▶️ Start Auto-Sync", key="gs_start", use_container_width=True)
    with stop_col:
        stop_btn  = st.button("⏹️ Stop Auto-Sync",  key="gs_stop",  use_container_width=True)

    if start_btn:
        if not gs_url_input:
            st.warning("Enter a Google Sheet URL first.")
        elif not SHOP_URL or not ACCESS_TOKEN:
            st.warning("Enter your Shopify API credentials first.")
        else:
            st.session_state.auto_sync_enabled  = True
            st.session_state.auto_sync_interval = interval_secs
            st.session_state.auto_sync_type     = sync_type
            st.session_state.gs_url             = gs_url_input
            st.session_state.gs_auth_type       = "public" if gs_auth_type == "Public" else "private"
            st.session_state.gs_sheet_name      = gs_sheet_name
            st.session_state.next_sync_time     = time.time() + interval_secs

            cfg = load_config()
            cfg["auto_sync"] = {
                "enabled":          True,
                "interval_seconds": interval_secs,
                "sync_type":        sync_type,
                "sheet_url":        gs_url_input,
                "auth_type":        "public" if gs_auth_type == "Public" else "private",
                "sheet_name":       gs_sheet_name,
            }
            save_config(cfg)
            st.success(
                f"✅ Auto-sync started — first sync in "
                f"**{interval_secs // 60} min{'s' if interval_secs >= 120 else ''}**. "
                "Countdown shows in the sidebar."
            )
            st.rerun()

    if stop_btn:
        st.session_state.auto_sync_enabled = False
        st.session_state.next_sync_time    = None
        cfg = load_config()
        cfg.setdefault("auto_sync", {})["enabled"] = False
        save_config(cfg)
        st.info("Auto-sync stopped.")
        st.rerun()

    # Status badge
    if st.session_state.auto_sync_enabled and st.session_state.next_sync_time:
        rem  = max(0, int(st.session_state.next_sync_time - time.time()))
        mins, secs = divmod(rem, 60)
        st.markdown(
            f'<span class="badge badge-gs">🟢 Auto-Sync ACTIVE — next in {mins:02d}m {secs:02d}s</span>',
            unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge badge-warning">⚪ Auto-Sync OFF</span>',
                    unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# TAB 4 — HOW TO USE
# ─────────────────────────────────────────────────────────────
with tab_guide:
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("""
        <div class="card">
            <div class="section-header"><span class="dot" style="background:#5c6ac4;"></span>🏷️ Price Update — File Format</div>
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <thead><tr style="background:#f0f0f0;">
                    <th style="padding:8px 12px;text-align:left;">Column</th>
                    <th style="padding:8px 12px;text-align:left;">Description</th>
                    <th style="padding:8px 12px;text-align:left;">Example</th>
                </tr></thead>
                <tbody>
                    <tr style="border-bottom:1px solid #f0f0f0;">
                        <td style="padding:8px 12px;"><code>ERP Code</code></td>
                        <td style="padding:8px 12px;">Your SKU</td>
                        <td style="padding:8px 12px;"><code>LAPTOP001</code></td>
                    </tr>
                    <tr>
                        <td style="padding:8px 12px;"><code>Display Price</code></td>
                        <td style="padding:8px 12px;">New price (₹ optional)</td>
                        <td style="padding:8px 12px;"><code>54999</code></td>
                    </tr>
                </tbody>
            </table>
        </div>
        <div class="card" style="margin-top:0;">
            <div class="section-header"><span class="dot"></span>📦 Stock Update — File Format</div>
            <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                <thead><tr style="background:#f0f0f0;">
                    <th style="padding:8px 12px;text-align:left;">Column</th>
                    <th style="padding:8px 12px;text-align:left;">Description</th>
                    <th style="padding:8px 12px;text-align:left;">Example</th>
                </tr></thead>
                <tbody>
                    <tr style="border-bottom:1px solid #f0f0f0;">
                        <td style="padding:8px 12px;"><code>ERP Code</code></td>
                        <td style="padding:8px 12px;">Your SKU</td>
                        <td style="padding:8px 12px;"><code>MOUSE002</code></td>
                    </tr>
                    <tr>
                        <td style="padding:8px 12px;"><code>Stock Quantity</code></td>
                        <td style="padding:8px 12px;">Available units</td>
                        <td style="padding:8px 12px;"><code>150</code></td>
                    </tr>
                </tbody>
            </table>
            <p style="font-size:0.78rem;color:var(--text-muted);margin-top:0.6rem;">
                Also accepted: <code>Quantity</code>, <code>Inventory Quantity</code>, <code>Stock</code>
            </p>
        </div>
        <div class="card" style="margin-top:0;">
            <div class="section-header"><span class="dot" style="background:#34a853;"></span>📊 Google Sheets Setup</div>
            <ol style="font-size:0.87rem;line-height:2;padding-left:1.2rem;">
                <li>Create a sheet with <code>ERP Code</code> | <code>Display Price</code> | <code>Stock Quantity</code></li>
                <li>Share → <strong>Anyone with link → Viewer</strong></li>
                <li>Paste the URL in the 📊 tab</li>
                <li>Choose what to sync &amp; set interval</li>
                <li>Click <strong>▶️ Start Auto-Sync</strong></li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with g2:
        st.markdown("""
        <div class="card">
            <div class="section-header"><span class="dot" style="background:#f59e0b;"></span>🔑 Getting Your Shopify Token</div>
            <ol style="font-size:0.87rem;line-height:2;padding-left:1.2rem;">
                <li>Go to <strong>Shopify Admin</strong></li>
                <li><strong>Settings → Apps and sales channels</strong></li>
                <li><strong>Develop apps → Create an app</strong></li>
                <li>Enable <code>write_products</code> &amp; <code>write_inventory</code></li>
                <li>Install the app → copy the <strong>Admin API access token</strong></li>
                <li>Paste in the sidebar → click <strong>💾 Save API Settings</strong></li>
            </ol>
        </div>
        <div class="card" style="margin-top:0;">
            <div class="section-header"><span class="dot" style="background:#ef4444;"></span>⚠️ Important Notes</div>
            <ul style="font-size:0.87rem;line-height:1.9;padding-left:1.2rem;">
                <li>SKUs matched <strong>exactly</strong> — case &amp; spaces matter</li>
                <li>Prices strip <code>₹</code> and commas automatically</li>
                <li>Unchanged prices are <strong>skipped</strong> to save API calls</li>
                <li>Inventory set to the <strong>first Shopify location</strong></li>
                <li>Credentials saved to <code>shopsync_config.json</code> locally</li>
                <li>Auto-sync countdown shown in the sidebar while active</li>
                <li>Rate limit: 0.2 s delay per API call (Shopify-compliant)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# AUTO-SYNC ENGINE  (fires at end of every script execution)
# ============================================================
if st.session_state.get("auto_sync_enabled") and st.session_state.get("next_sync_time"):
    now  = time.time()
    rem  = st.session_state.next_sync_time - now

    if rem <= 0:
        # ── Fire! ─────────────────────────────────────────────
        gs_url_as = st.session_state.gs_url
        gs_sa     = st.session_state.gs_service_account
        gs_at     = st.session_state.gs_auth_type
        gs_sn     = st.session_state.gs_sheet_name

        ph = st.empty()
        with ph.container():
            st.info("🔄 Auto-sync running…")

        if gs_at == "private" and gs_sa:
            import re as _re
            _m = _re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", gs_url_as)
            df_auto, aerr = (fetch_google_sheet_private(gs_sa, _m.group(1), gs_sn)
                             if _m else (None, "Invalid URL"))
        else:
            df_auto, aerr = fetch_google_sheet_public(gs_url_as)

        if aerr:
            ph.error(f"Auto-sync error: {aerr}")
        elif df_auto is not None:
            _do_sync(df_auto, "Auto-Sync")
            ph.success(f"✅ Auto-sync complete at {datetime.now().strftime('%H:%M:%S')}")

        st.session_state.next_sync_time = time.time() + st.session_state.auto_sync_interval
        time.sleep(2)
        st.rerun()

    else:
        # ── Not yet — schedule a UI refresh to update the countdown ──
        sleep_for = 60 if rem > 300 else (30 if rem > 60 else 10)
        time.sleep(sleep_for)
        st.rerun()
