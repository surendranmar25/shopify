import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime
from io import BytesIO

# ============================================================
# PAGE CONFIG  (must be first Streamlit call)
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
/* ---------- Google Font ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ---------- Root variables ---------- */
:root {
    --shopify-green:  #008060;
    --shopify-green2: #004c3f;
    --accent:         #5c6ac4;
    --bg-light:       #f6f6f7;
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

/* ---------- Global font ---------- */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: var(--text-main);
}

/* ---------- Hide default Streamlit chrome ---------- */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem 3rem; }

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--shopify-green2) 0%, #006b50 100%);
    color: #fff;
}
[data-testid="stSidebar"] * { color: #fff !important; }
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #fff !important;
    border-radius: 8px;
}
[data-testid="stSidebar"] .stTextInput input::placeholder { color: rgba(255,255,255,0.55) !important; }
[data-testid="stSidebar"] label { color: rgba(255,255,255,0.85) !important; font-size: 0.82rem !important; }

/* ---------- Tab strip ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f0f0f0;
    padding: 5px;
    border-radius: 10px;
    border-bottom: none;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 0.55rem 1.6rem;
    font-weight: 500;
    font-size: 0.92rem;
    background: transparent;
    border: none;
    color: var(--text-muted);
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    background: #fff !important;
    color: var(--shopify-green) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

/* ---------- Generic card ---------- */
.card {
    background: var(--card-bg);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 1.4rem 1.6rem;
    box-shadow: var(--shadow);
    margin-bottom: 1.2rem;
}

/* ---------- Metric cards row ---------- */
.metric-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.4rem; }
.metric-card {
    flex: 1; min-width: 140px;
    background: var(--card-bg);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 1.1rem 1.3rem;
    box-shadow: var(--shadow);
    text-align: center;
}
.metric-card .m-icon { font-size: 1.7rem; margin-bottom: 0.3rem; }
.metric-card .m-value { font-size: 1.75rem; font-weight: 700; color: var(--shopify-green); }
.metric-card .m-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.1rem; }

/* ---------- Status badge ---------- */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
}
.badge-success { background: #e3f5ef; color: var(--success); }
.badge-warning { background: #fff3cd; color: #7a5100; }
.badge-danger  { background: #fce8e6; color: var(--danger); }
.badge-info    { background: #edf0ff; color: var(--accent); }

/* ---------- Section headers ---------- */
.section-header {
    display: flex; align-items: center; gap: 0.6rem;
    font-size: 1.05rem; font-weight: 600; color: var(--text-main);
    margin-bottom: 0.8rem;
}
.section-header .dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: var(--shopify-green);
    display: inline-block;
}

/* ---------- Upload zone ---------- */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    background: #fafafa !important;
    padding: 0.8rem !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--shopify-green) !important;
    background: #f0faf6 !important;
}

/* ---------- Buttons ---------- */
.stButton > button {
    background: linear-gradient(135deg, var(--shopify-green) 0%, #005c45 100%);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.55rem 1.8rem;
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.02em;
    transition: all 0.25s;
    box-shadow: 0 2px 8px rgba(0,128,96,0.3);
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(0,128,96,0.4);
}
.stButton > button:active { transform: translateY(0); }

/* ---------- Download button ---------- */
[data-testid="stDownloadButton"] > button {
    background: #fff !important;
    color: var(--shopify-green) !important;
    border: 2px solid var(--shopify-green) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #f0faf6 !important;
}

/* ---------- Progress bar ---------- */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, var(--shopify-green), #00a47a) !important;
    border-radius: 99px !important;
}

/* ---------- Alerts / success ---------- */
[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* ---------- DataFrame ---------- */
[data-testid="stDataFrame"] { border-radius: var(--radius); overflow: hidden; }

/* ---------- Divider ---------- */
hr { border-color: var(--border); margin: 1rem 0; }

/* ---------- Sidebar logo block ---------- */
.sidebar-logo {
    display: flex; align-items: center; gap: 0.7rem;
    padding: 0.2rem 0 1.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.2);
    margin-bottom: 1.2rem;
}
.sidebar-logo .logo-icon { font-size: 2rem; }
.sidebar-logo .logo-text { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.01em; }
.sidebar-logo .logo-sub  { font-size: 0.72rem; opacity: 0.65; margin-top: -2px; }

/* ---------- Connection status pill ---------- */
.conn-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.78rem;
    font-weight: 500;
}
.conn-pill .dot-live {
    width: 8px; height: 8px; border-radius: 50%;
    background: #3dca8a;
    box-shadow: 0 0 0 3px rgba(61,202,138,0.3);
    animation: pulse 1.8s infinite;
}
.conn-pill .dot-off { width: 8px; height: 8px; border-radius: 50%; background: #ff7b7b; }
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 3px rgba(61,202,138,0.3); }
    50%        { box-shadow: 0 0 0 6px rgba(61,202,138,0.1); }
}

/* ---------- Page-level header ---------- */
.page-header {
    background: linear-gradient(135deg, var(--shopify-green2) 0%, #006b50 100%);
    border-radius: var(--radius);
    padding: 1.6rem 2rem;
    margin-bottom: 1.6rem;
    color: #fff;
    display: flex; align-items: center; justify-content: space-between;
}
.page-header h1 { font-size: 1.55rem; font-weight: 700; margin: 0; }
.page-header p  { font-size: 0.87rem; opacity: 0.8; margin: 0.25rem 0 0; }
.page-header .header-icon { font-size: 2.6rem; }

/* ---------- Info boxes ---------- */
.info-box {
    background: #edf2ff;
    border-left: 4px solid var(--accent);
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    color: #2c3e9e;
    margin-bottom: 1rem;
}
.info-box strong { display: block; margin-bottom: 0.2rem; }

.warning-box {
    background: #fff8ee;
    border-left: 4px solid #ffc453;
    border-radius: 0 8px 8px 0;
    padding: 0.75rem 1rem;
    font-size: 0.85rem;
    color: #7a5100;
    margin-bottom: 1rem;
}

/* ---------- Log area ---------- */
.log-container {
    background: #1a1a2e;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #a8ff78;
    max-height: 260px;
    overflow-y: auto;
    line-height: 1.7;
}

/* ---------- Step indicator ---------- */
.steps { display: flex; gap: 0; margin-bottom: 1.2rem; }
.step {
    flex: 1; text-align: center;
    padding: 0.5rem 0.3rem;
    font-size: 0.78rem; font-weight: 500;
    border-top: 3px solid var(--border);
    color: var(--text-muted);
}
.step.active { border-top-color: var(--shopify-green); color: var(--shopify-green); }
.step.done   { border-top-color: var(--shopify-green); color: var(--text-muted); }

/* ---------- Settings expander ---------- */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--card-bg) !important;
    box-shadow: var(--shadow) !important;
    margin-bottom: 1.2rem !important;
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.92rem !important;
}
</style>
""", unsafe_allow_html=True)

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
    SHOP_URL = st.text_input(
        "Shop URL",
        placeholder="yourstore.myshopify.com",
        key="sidebar_shop_url",
        help="Enter your Shopify store URL without https://"
    )
    ACCESS_TOKEN = st.text_input(
        "Access Token",
        placeholder="shpat_xxxxxxxxxxxx",
        type="password",
        key="sidebar_token",
        help="Find this in Shopify Admin → Apps → Private Apps"
    )
    API_VERSION = st.text_input("API Version", value="2025-04", key="sidebar_api_version")

    st.markdown("""
    <div style="font-size:0.78rem; background:rgba(255,255,255,0.1);
         border-radius:8px; padding:8px 10px; margin-top:4px; line-height:1.6;">
        💡 <strong>Tip:</strong> Settings are also available in the
        <em>⚙️ API Settings</em> panel on the main page — visible even
        when this sidebar is closed.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Live connection status pill
    if SHOP_URL and ACCESS_TOKEN:
        st.markdown("""
        <div class="conn-pill">
            <span class="dot-live"></span> Connected
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="conn-pill">
            <span class="dot-off"></span> Not connected
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.78rem; opacity:0.7; line-height:1.6;">
    <strong style="opacity:1;">📋 Quick Guide</strong><br>
    1. Paste your Shop URL &amp; Token<br>
    2. Choose Price or Stock tab<br>
    3. Upload your Excel / CSV file<br>
    4. Hit the Update button<br>
    5. Download the result report
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; opacity:0.55; text-align:center;">
    ShopSync v1.0 · Built for Shopify
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================
def get_headers(access_token):
    return {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }


def load_file(uploaded_file):
    uploaded_file.seek(0)
    fname = uploaded_file.name.lower()
    try:
        if fname.endswith(".csv"):
            try:
                df = pd.read_csv(uploaded_file, encoding="utf-8")
            except Exception:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding="latin1")
        elif fname.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV or Excel.")
            return None
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None


def process_price_file(df):
    required_cols = ["ERP Code", "Display Price"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {missing}. Required: {required_cols}")
        return {}, None

    sku_price = {}
    for _, row in df.iterrows():
        if pd.isna(row["Display Price"]):
            continue
        sku   = str(row["ERP Code"]).strip()
        price = str(row["Display Price"]).strip().replace(",", "").replace("₹", "")
        try:
            price = float(price)
        except Exception:
            continue
        if sku:
            sku_price[sku] = price
    return sku_price, df


def process_stock_file(df):
    candidates = ["Stock Quantity", "Quantity", "Inventory Quantity", "Stock"]
    stock_col  = next((c for c in candidates if c in df.columns), None)
    if not stock_col:
        st.error(f"Missing stock column. Use one of: {', '.join(candidates)}")
        return {}, None
    if "ERP Code" not in df.columns:
        st.error("Missing 'ERP Code' column.")
        return {}, None

    sku_stock = {}
    for _, row in df.iterrows():
        if pd.isna(row[stock_col]):
            continue
        sku = str(row["ERP Code"]).strip()
        qty = str(row[stock_col]).strip().replace(",", "")
        try:
            qty = int(float(qty))
        except Exception:
            continue
        if sku:
            sku_stock[sku] = qty
    return sku_stock, df


@st.cache_data
def get_all_shopify_skus(shop_url, api_version, access_token):
    sku_map = {}
    headers = get_headers(access_token)
    url = (
        f"https://{shop_url}/admin/api/{api_version}"
        "/products.json?limit=250&fields=id,variants"
    )
    while url:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            st.error(f"Error fetching products: {resp.status_code} — {resp.text[:200]}")
            break
        for p in resp.json().get("products", []):
            for v in p.get("variants", []):
                sku = (v.get("sku") or "").strip()
                if sku:
                    sku_map[sku] = {
                        "variant_id":        v["id"],
                        "price":             float(v.get("price", 0)),
                        "inventory_item_id": v.get("inventory_item_id"),
                    }
        link = resp.headers.get("Link", "")
        url  = None
        if 'rel="next"' in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split("<")[1].split(">")[0]
        time.sleep(0.2)
    return sku_map


def get_shopify_location_id(shop_url, api_version, access_token):
    headers = get_headers(access_token)
    resp = requests.get(
        f"https://{shop_url}/admin/api/{api_version}/locations.json",
        headers=headers,
    )
    if resp.status_code != 200:
        st.error(f"Error fetching locations: {resp.status_code}")
        return None
    locs = resp.json().get("locations", [])
    if not locs:
        st.error("No Shopify locations found.")
        return None
    return locs[0]["id"]


def set_inventory_level(shop_url, api_version, access_token,
                        location_id, inventory_item_id, available):
    return requests.post(
        f"https://{shop_url}/admin/api/{api_version}/inventory_levels/set.json",
        headers=get_headers(access_token),
        json={
            "location_id":        location_id,
            "inventory_item_id":  inventory_item_id,
            "available":          available,
        },
    )


def excel_download(df, prefix):
    fname  = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return output, fname


# ============================================================
# PAGE HEADER
# ============================================================
st.markdown("""
<div class="page-header">
    <div>
        <h1>🛍️ ShopSync — Shopify Bulk Updater</h1>
        <p>Sync prices and inventory from your ERP directly into Shopify in seconds</p>
    </div>
    <div class="header-icon">📦</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# INLINE API SETTINGS  (always visible — sidebar may be collapsed)
# Merge: sidebar values take priority if filled, else use inline
# ============================================================
_sidebar_url     = st.session_state.get("sidebar_shop_url", "")
_sidebar_token   = st.session_state.get("sidebar_token", "")
_sidebar_version = st.session_state.get("sidebar_api_version", "2025-04")

connected = bool((_sidebar_url or "") and (_sidebar_token or ""))
expander_label = (
    "⚙️ API Settings  ·  ✅ Connected"
    if connected
    else "⚙️ API Settings  ·  ⚠️ Not configured — click to set up"
)

with st.expander(expander_label, expanded=not connected):
    ec1, ec2, ec3 = st.columns([3, 3, 2])
    with ec1:
        SHOP_URL = st.text_input(
            "🌐 Shop URL",
            value=_sidebar_url,
            placeholder="yourstore.myshopify.com",
            key="inline_shop_url",
            help="Your Shopify store URL — no https://",
        )
    with ec2:
        ACCESS_TOKEN = st.text_input(
            "🔑 Access Token",
            value=_sidebar_token,
            placeholder="shpat_xxxxxxxxxxxx",
            type="password",
            key="inline_token",
            help="Shopify Admin → Apps → Develop apps → Admin API token",
        )
    with ec3:
        API_VERSION = st.text_input(
            "📅 API Version",
            value=_sidebar_version,
            key="inline_api_version",
        )
    if SHOP_URL and ACCESS_TOKEN:
        st.markdown(
            '<span class="badge badge-success">✅ Credentials entered — you can collapse this panel</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-warning">⚠️ Fill in Shop URL and Access Token to enable updates</span>',
            unsafe_allow_html=True,
        )

# Resolve final values (inline wins over sidebar when both present)
SHOP_URL     = SHOP_URL     or _sidebar_url
ACCESS_TOKEN = ACCESS_TOKEN or _sidebar_token
API_VERSION  = API_VERSION  or _sidebar_version or "2025-04"

# ============================================================
# SUMMARY METRICS (top of page)
# ============================================================
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("""
    <div class="metric-card">
        <div class="m-icon">🏷️</div>
        <div class="m-value">—</div>
        <div class="m-label">Prices Updated</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="metric-card">
        <div class="m-icon">📦</div>
        <div class="m-value">—</div>
        <div class="m-label">Stock Updated</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="metric-card">
        <div class="m-icon">✅</div>
        <div class="m-value">—</div>
        <div class="m-label">SKUs Matched</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown("""
    <div class="metric-card">
        <div class="m-icon">⏱️</div>
        <div class="m-value">—</div>
        <div class="m-label">Last Run</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILE UPLOADERS  (above tabs — always visible)
# ============================================================
up_col1, up_col2 = st.columns(2)

with up_col1:
    st.markdown("""
    <div class="section-header">
        <span class="dot" style="background:#5c6ac4;"></span>
        Price Update File
    </div>
    """, unsafe_allow_html=True)
    price_file = st.file_uploader(
        "Upload Price CSV / Excel",
        type=["csv", "xlsx", "xls"],
        key="price_file",
        label_visibility="collapsed",
    )
    st.markdown("""
    <div class="info-box">
        <strong>Required columns</strong>
        <code>ERP Code</code> &nbsp;|&nbsp; <code>Display Price</code>
    </div>""", unsafe_allow_html=True)

with up_col2:
    st.markdown("""
    <div class="section-header">
        <span class="dot" style="background:#008060;"></span>
        Stock Update File
    </div>
    """, unsafe_allow_html=True)
    stock_file = st.file_uploader(
        "Upload Stock CSV / Excel",
        type=["csv", "xlsx", "xls"],
        key="stock_file",
        label_visibility="collapsed",
    )
    st.markdown("""
    <div class="info-box" style="background:#edf8f4; border-left-color:#008060; color:#004c3f;">
        <strong>Required columns</strong>
        <code>ERP Code</code> &nbsp;|&nbsp; <code>Stock Quantity</code>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# TABS
# ============================================================
tab_price, tab_stock, tab_guide = st.tabs([
    "🏷️  Price Update",
    "📦  Stock Update",
    "📖  How to Use",
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — PRICE UPDATE
# ─────────────────────────────────────────────────────────────
with tab_price:
    st.markdown("""
    <div class="section-header" style="font-size:1.15rem; margin-top:0.5rem;">
        <span class="dot" style="background:#5c6ac4;"></span>
        Bulk Price Update
        &nbsp;<span class="badge badge-info">Shopify Admin API</span>
    </div>
    """, unsafe_allow_html=True)

    if price_file is None:
        st.markdown("""
        <div class="warning-box">
            ⬆️ Upload a <strong>Price Update file</strong> using the uploader above to get started.
        </div>""", unsafe_allow_html=True)
    else:
        df_price = load_file(price_file)
        if df_price is not None:
            # File preview card
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns([2, 1, 1])
            with fc1:
                st.markdown(f"**📄 File:** `{price_file.name}`")
            with fc2:
                st.markdown(f"**Rows:** `{len(df_price)}`")
            with fc3:
                st.markdown(f"**Cols:** `{len(df_price.columns)}`")
            st.dataframe(
                df_price.head(8),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Steps
            st.markdown("""
            <div class="steps">
                <div class="step done">① File Uploaded</div>
                <div class="step active">② Run Update</div>
                <div class="step">③ Download Report</div>
            </div>""", unsafe_allow_html=True)

            btn_col, _ = st.columns([1, 3])
            with btn_col:
                run_price = st.button("🚀 Start Price Update", key="price_update", use_container_width=True)

            if run_price:
                if not SHOP_URL or not ACCESS_TOKEN:
                    st.error("⚠️ Enter your **Shop URL** and **Access Token** in the sidebar first.")
                    st.stop()

                sku_price, _ = process_price_file(df_price)
                if not sku_price:
                    st.stop()

                with st.spinner("Fetching products from Shopify…"):
                    shopify_skus = get_all_shopify_skus(SHOP_URL, API_VERSION, ACCESS_TOKEN)

                matched = set(sku_price.keys()) & set(shopify_skus.keys())
                unmatched = set(sku_price.keys()) - set(shopify_skus.keys())

                m1, m2, m3 = st.columns(3)
                m1.metric("📋 File SKUs",     len(sku_price))
                m2.metric("✅ Matched",        len(matched))
                m3.metric("❌ Not in Shopify", len(unmatched))

                if not matched:
                    st.warning("No matching SKUs found between the file and Shopify.")
                    st.stop()

                st.markdown("**⚡ Update Progress**")
                progress_bar = st.progress(0)
                status_text  = st.empty()
                log_lines    = []
                log_area     = st.empty()

                results  = []
                updated  = 0
                skipped  = 0
                errors   = 0
                total    = len(matched)

                for i, sku in enumerate(sorted(matched), start=1):
                    new_price  = sku_price[sku]
                    variant_id = shopify_skus[sku]["variant_id"]
                    old_price  = shopify_skus[sku]["price"]

                    if old_price == new_price:
                        skipped += 1
                        progress_bar.progress(i / total)
                        status_text.markdown(f"⏭️ Skipped `{sku}` — price unchanged")
                        continue

                    resp = requests.put(
                        f"https://{SHOP_URL}/admin/api/{API_VERSION}/variants/{variant_id}.json",
                        headers=get_headers(ACCESS_TOKEN),
                        json={"variant": {"id": variant_id, "price": str(new_price)}},
                    )

                    if resp.status_code == 200:
                        updated += 1
                        line = f"✅  [{i:03d}]  {sku:<20}  ₹{old_price:>10,.2f}  →  ₹{new_price:>10,.2f}"
                        results.append({
                            "S.No": i,
                            "ERP Code":      sku,
                            "Old Price":     old_price,
                            "Updated Price": new_price,
                            "Updated Date":  datetime.now().strftime("%Y-%m-%d"),
                        })
                    else:
                        errors += 1
                        line = f"❌  [{i:03d}]  {sku:<20}  HTTP {resp.status_code}"

                    log_lines.append(line)
                    log_area.markdown(
                        "<div class='log-container'>"
                        + "<br>".join(log_lines[-20:])
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    progress_bar.progress(i / total)
                    status_text.markdown(f"Processing **{i}** of **{total}** — {sku}")
                    time.sleep(0.2)

                status_text.empty()
                progress_bar.progress(1.0)

                # Final summary
                st.markdown('<div class="card">', unsafe_allow_html=True)
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("✅ Updated",  updated)
                r2.metric("⏭️ Skipped",  skipped)
                r3.metric("❌ Errors",   errors)
                r4.metric("📋 Total",    total)
                st.markdown('</div>', unsafe_allow_html=True)

                if results:
                    st.success(f"🎉 Price update complete! **{updated}** products updated successfully.")
                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    output, fname = excel_download(result_df, "price_update")
                    st.download_button(
                        label="📥 Download Price Update Report",
                        data=output,
                        file_name=fname,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

# ─────────────────────────────────────────────────────────────
# TAB 2 — STOCK UPDATE
# ─────────────────────────────────────────────────────────────
with tab_stock:
    st.markdown("""
    <div class="section-header" style="font-size:1.15rem; margin-top:0.5rem;">
        <span class="dot"></span>
        Bulk Inventory / Stock Update
        &nbsp;<span class="badge badge-success">Inventory API</span>
    </div>
    """, unsafe_allow_html=True)

    if stock_file is None:
        st.markdown("""
        <div class="warning-box">
            ⬆️ Upload a <strong>Stock Update file</strong> using the uploader above to get started.
        </div>""", unsafe_allow_html=True)
    else:
        df_stock = load_file(stock_file)
        if df_stock is not None:
            # File preview card
            st.markdown('<div class="card">', unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns([2, 1, 1])
            with fc1:
                st.markdown(f"**📄 File:** `{stock_file.name}`")
            with fc2:
                st.markdown(f"**Rows:** `{len(df_stock)}`")
            with fc3:
                st.markdown(f"**Cols:** `{len(df_stock.columns)}`")
            st.dataframe(
                df_stock.head(8),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # Steps
            st.markdown("""
            <div class="steps">
                <div class="step done">① File Uploaded</div>
                <div class="step active">② Run Update</div>
                <div class="step">③ Download Report</div>
            </div>""", unsafe_allow_html=True)

            btn_col, _ = st.columns([1, 3])
            with btn_col:
                run_stock = st.button("🚀 Start Stock Update", key="stock_update", use_container_width=True)

            if run_stock:
                if not SHOP_URL or not ACCESS_TOKEN:
                    st.error("⚠️ Enter your **Shop URL** and **Access Token** in the sidebar first.")
                    st.stop()

                sku_stock, _ = process_stock_file(df_stock)
                if not sku_stock:
                    st.stop()

                with st.spinner("Fetching products & location from Shopify…"):
                    shopify_skus = get_all_shopify_skus(SHOP_URL, API_VERSION, ACCESS_TOKEN)
                    location_id  = get_shopify_location_id(SHOP_URL, API_VERSION, ACCESS_TOKEN)

                if location_id is None:
                    st.stop()

                matched   = set(sku_stock.keys()) & set(shopify_skus.keys())
                unmatched = set(sku_stock.keys()) - set(shopify_skus.keys())

                m1, m2, m3 = st.columns(3)
                m1.metric("📋 File SKUs",     len(sku_stock))
                m2.metric("✅ Matched",        len(matched))
                m3.metric("❌ Not in Shopify", len(unmatched))

                if not matched:
                    st.warning("No matching SKUs found between the file and Shopify.")
                    st.stop()

                st.markdown("**⚡ Update Progress**")
                progress_bar = st.progress(0)
                status_text  = st.empty()
                log_lines    = []
                log_area     = st.empty()

                results  = []
                updated  = 0
                errors   = 0
                total    = len(matched)

                for i, sku in enumerate(sorted(matched), start=1):
                    new_qty           = sku_stock[sku]
                    inventory_item_id = shopify_skus[sku].get("inventory_item_id")

                    if not inventory_item_id:
                        errors += 1
                        log_lines.append(f"❌  [{i:03d}]  {sku:<20}  missing inventory_item_id")
                        log_area.markdown(
                            "<div class='log-container'>"
                            + "<br>".join(log_lines[-20:])
                            + "</div>",
                            unsafe_allow_html=True,
                        )
                        progress_bar.progress(i / total)
                        continue

                    resp = set_inventory_level(
                        SHOP_URL, API_VERSION, ACCESS_TOKEN,
                        location_id, inventory_item_id, new_qty,
                    )

                    if resp.status_code == 200:
                        updated += 1
                        line = f"✅  [{i:03d}]  {sku:<20}  qty → {new_qty}"
                        results.append({
                            "S.No": i,
                            "ERP Code":         sku,
                            "Updated Quantity":  new_qty,
                            "Updated Date":      datetime.now().strftime("%Y-%m-%d"),
                        })
                    else:
                        errors += 1
                        line = f"❌  [{i:03d}]  {sku:<20}  HTTP {resp.status_code}"

                    log_lines.append(line)
                    log_area.markdown(
                        "<div class='log-container'>"
                        + "<br>".join(log_lines[-20:])
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                    progress_bar.progress(i / total)
                    status_text.markdown(f"Processing **{i}** of **{total}** — {sku}")
                    time.sleep(0.2)

                status_text.empty()
                progress_bar.progress(1.0)

                # Final summary
                st.markdown('<div class="card">', unsafe_allow_html=True)
                r1, r2, r3 = st.columns(3)
                r1.metric("✅ Updated", updated)
                r2.metric("❌ Errors",  errors)
                r3.metric("📋 Total",   total)
                st.markdown('</div>', unsafe_allow_html=True)

                if results:
                    st.success(f"🎉 Stock update complete! **{updated}** inventory records updated.")
                    result_df = pd.DataFrame(results)
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    output, fname = excel_download(result_df, "stock_update")
                    st.download_button(
                        label="📥 Download Stock Update Report",
                        data=output,
                        file_name=fname,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

# ─────────────────────────────────────────────────────────────
# TAB 3 — HOW TO USE
# ─────────────────────────────────────────────────────────────
with tab_guide:
    g1, g2 = st.columns(2)

    with g1:
        st.markdown("""
        <div class="card">
            <div class="section-header">
                <span class="dot" style="background:#5c6ac4;"></span>
                🏷️ Price Update — File Format
            </div>
            <p style="font-size:0.87rem; color:var(--text-muted); margin-bottom:0.8rem;">
                Your Excel / CSV must contain these <strong>exact column names</strong>:
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                <thead>
                    <tr style="background:#f0f0f0;">
                        <th style="padding:8px 12px; text-align:left; border-radius:6px 0 0 0;">Column</th>
                        <th style="padding:8px 12px; text-align:left;">Description</th>
                        <th style="padding:8px 12px; text-align:left; border-radius:0 6px 0 0;">Example</th>
                    </tr>
                </thead>
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
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="card" style="margin-top:0;">
            <div class="section-header">
                <span class="dot"></span>
                📦 Stock Update — File Format
            </div>
            <p style="font-size:0.87rem; color:var(--text-muted); margin-bottom:0.8rem;">
                Your Excel / CSV must contain these <strong>exact column names</strong>:
            </p>
            <table style="width:100%; border-collapse:collapse; font-size:0.85rem;">
                <thead>
                    <tr style="background:#f0f0f0;">
                        <th style="padding:8px 12px; text-align:left;">Column</th>
                        <th style="padding:8px 12px; text-align:left;">Description</th>
                        <th style="padding:8px 12px; text-align:left;">Example</th>
                    </tr>
                </thead>
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
            <p style="font-size:0.78rem; color:var(--text-muted); margin-top:0.6rem;">
                Alternate accepted column names: <code>Quantity</code>, <code>Inventory Quantity</code>, <code>Stock</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    with g2:
        st.markdown("""
        <div class="card">
            <div class="section-header">
                <span class="dot" style="background:#f59e0b;"></span>
                🔑 Getting Your Shopify Access Token
            </div>
            <ol style="font-size:0.87rem; line-height:2; color:var(--text-main); padding-left:1.2rem;">
                <li>Go to your <strong>Shopify Admin</strong></li>
                <li>Navigate to <strong>Settings → Apps and sales channels</strong></li>
                <li>Click <strong>Develop apps</strong> → <strong>Create an app</strong></li>
                <li>Under <strong>Configuration</strong> enable:<br>
                    &nbsp;&nbsp;• <code>write_products</code><br>
                    &nbsp;&nbsp;• <code>write_inventory</code>
                </li>
                <li>Install the app and copy the <strong>Admin API access token</strong></li>
                <li>Paste it in the <strong>sidebar</strong> of this tool</li>
            </ol>
        </div>

        <div class="card" style="margin-top:0;">
            <div class="section-header">
                <span class="dot" style="background:#ef4444;"></span>
                ⚠️ Important Notes
            </div>
            <ul style="font-size:0.87rem; line-height:1.9; color:var(--text-main); padding-left:1.2rem;">
                <li>SKUs are matched <strong>exactly</strong> — case &amp; spaces matter</li>
                <li>Prices can include <code>₹</code> and commas — they are stripped automatically</li>
                <li>Unchanged prices are <strong>skipped</strong> to save API calls</li>
                <li>Inventory is set to the <strong>first Shopify location</strong> by default</li>
                <li>A downloadable Excel report is generated after every run</li>
                <li>Rate limit: 0.2 s delay per request (Shopify limit compliant)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
