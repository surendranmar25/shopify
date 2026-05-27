"""
shopify_api.py — ShopSync Backend
All Shopify API calls, file parsing, Google Sheets fetching, and config I/O.
No Streamlit imports — pure Python so it can be tested independently.
"""

import json
import os
import re
import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import requests

# ── Config file — absolute path so it always resolves next to this file ──────
_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_HERE, "shopsync_config.json")


def load_config() -> dict:
    """Load saved settings from JSON. Returns {} if not found or corrupt."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict) -> None:
    """Persist settings dict to JSON."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Shopify helpers ───────────────────────────────────────────────────────────
def get_headers(access_token: str) -> dict:
    return {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }


def load_file(uploaded_file) -> tuple:
    """
    Parse a CSV / Excel uploaded file.
    Returns (df, error_message). df is None on failure.
    """
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
            return None, "Unsupported format — please upload CSV or Excel."
        df.columns = df.columns.str.strip()
        return df, None
    except Exception as e:
        return None, f"Error reading file: {e}"


def process_price_file(df: pd.DataFrame) -> tuple:
    """
    Build a SKU → price mapping from a DataFrame.
    Returns (sku_price_dict, error_message).
    """
    required = ["ERP Code", "Display Price"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return {}, f"Missing columns: {missing}. Required: {required}"

    sku_price: dict = {}
    for _, row in df.iterrows():
        if pd.isna(row["Display Price"]):
            continue
        sku = str(row["ERP Code"]).strip()
        price = str(row["Display Price"]).strip().replace(",", "").replace("₹", "")
        try:
            price = float(price)
        except Exception:
            continue
        if sku:
            sku_price[sku] = price
    return sku_price, None


def process_stock_file(df: pd.DataFrame) -> tuple:
    """
    Build a SKU → quantity mapping from a DataFrame.
    Returns (sku_stock_dict, error_message).
    """
    candidates = ["Stock Quantity", "Quantity", "Inventory Quantity", "Stock"]
    stock_col = next((c for c in candidates if c in df.columns), None)
    if not stock_col:
        return {}, f"Missing stock column. Accepted names: {', '.join(candidates)}"
    if "ERP Code" not in df.columns:
        return {}, "Missing 'ERP Code' column."

    sku_stock: dict = {}
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
    return sku_stock, None


def fetch_all_shopify_skus(shop_url: str, api_version: str, access_token: str) -> tuple:
    """
    Paginate through all Shopify products and collect variant SKU data.
    Returns (sku_map, error_message).
    sku_map: { sku_string: { variant_id, price, inventory_item_id } }
    """
    sku_map: dict = {}
    headers = get_headers(access_token)
    url = (
        f"https://{shop_url}/admin/api/{api_version}"
        "/products.json?limit=250&fields=id,variants"
    )
    while url:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            return sku_map, f"Network error: {e}"
        if resp.status_code != 200:
            return sku_map, (
                f"Shopify API error {resp.status_code}: {resp.text[:200]}"
            )
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
        url = None
        if 'rel="next"' in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split("<")[1].split(">")[0]
        time.sleep(0.2)
    return sku_map, None


def get_shopify_location_id(shop_url: str, api_version: str, access_token: str) -> tuple:
    """Returns (location_id, error_message)."""
    try:
        resp = requests.get(
            f"https://{shop_url}/admin/api/{api_version}/locations.json",
            headers=get_headers(access_token),
            timeout=30,
        )
    except requests.RequestException as e:
        return None, f"Network error: {e}"
    if resp.status_code != 200:
        return None, f"Shopify API error {resp.status_code}"
    locs = resp.json().get("locations", [])
    if not locs:
        return None, "No Shopify locations found."
    return locs[0]["id"], None


def update_variant_price(shop_url: str, api_version: str, access_token: str,
                          variant_id: int, new_price: float):
    """PUT a new price on a single variant. Returns requests.Response."""
    return requests.put(
        f"https://{shop_url}/admin/api/{api_version}/variants/{variant_id}.json",
        headers=get_headers(access_token),
        json={"variant": {"id": variant_id, "price": str(new_price)}},
        timeout=30,
    )


def set_inventory_level(shop_url: str, api_version: str, access_token: str,
                         location_id: int, inventory_item_id: int, available: int):
    """POST inventory level. Returns requests.Response."""
    return requests.post(
        f"https://{shop_url}/admin/api/{api_version}/inventory_levels/set.json",
        headers=get_headers(access_token),
        json={
            "location_id":       location_id,
            "inventory_item_id": inventory_item_id,
            "available":         available,
        },
        timeout=30,
    )


def excel_download(df: pd.DataFrame, prefix: str) -> tuple:
    """Serialize a DataFrame to an Excel BytesIO buffer. Returns (buffer, filename)."""
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    return output, fname


# ── Google Sheets ─────────────────────────────────────────────────────────────
def fetch_google_sheet_public(sheet_url: str) -> tuple:
    """
    Fetch a *public* Google Sheet (shared → Anyone with link can view).
    Automatically converts the share URL to a CSV-export URL.
    Returns (df, error_message).
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        return None, (
            "Could not extract sheet ID from URL. "
            "Paste the full Google Sheets URL from the address bar."
        )
    sheet_id = match.group(1)
    gid_m = re.search(r"[#&?]gid=(\d+)", sheet_url)
    gid = gid_m.group(1) if gid_m else "0"
    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )
    try:
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()
        return df, None
    except Exception as e:
        return None, (
            f"Could not read sheet: {e}. "
            "Make sure the sheet is shared as 'Anyone with link can view'."
        )


def fetch_google_sheet_private(service_account_info: dict,
                                spreadsheet_id: str,
                                sheet_name: str = "Sheet1") -> tuple:
    """
    Fetch a private Google Sheet using a service-account JSON credential dict.
    Requires: pip install gspread google-auth
    Returns (df, error_message).
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(creds)
        worksheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        df = pd.DataFrame(worksheet.get_all_records())
        df.columns = df.columns.str.strip()
        return df, None
    except ImportError:
        return None, (
            "gspread is not installed. "
            "Run: pip install gspread google-auth"
        )
    except Exception as e:
        return None, f"Private sheet error: {e}"
