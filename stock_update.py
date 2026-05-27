"""
stock_update.py — Stock Update tab UI & logic for ShopSync.
Called from app.py via render().
"""

import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from shopify_api import (
    load_file,
    process_stock_file,
    get_shopify_location_id,
    set_inventory_level,
    excel_download,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "ERP Code":       ["LAPTOP001", "MOUSE002", "KB003", "MON004",
                           "CHAIR005", "HEADPH006", "WEBCAM007", "DESK008"],
        "Stock Quantity": [25, 150, 80, 40, 60, 35, 90, 15],
        "Product Name":   ["Gaming Laptop", "Wireless Mouse", "Mechanical Keyboard",
                           "4K Monitor", "Ergonomic Chair", "Noise Cancelling Headphones",
                           "HD Webcam", "Standing Desk"],
        "Category":       ["Electronics", "Accessories", "Accessories", "Electronics",
                           "Furniture", "Accessories", "Electronics", "Furniture"],
    })


def _to_excel(df: pd.DataFrame) -> BytesIO:
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf


def render(stock_file, shop_url: str, api_version: str,
           access_token: str, get_skus_fn) -> None:
    """
    Render the full Stock Update tab.

    Parameters
    ----------
    stock_file    : Streamlit UploadedFile or None
    shop_url      : Shopify store URL (e.g. yourstore.myshopify.com)
    api_version   : e.g. '2025-04'
    access_token  : Shopify Admin API access token
    get_skus_fn   : cached callable(shop_url, api_version, access_token)
                    → (sku_map, error_msg)
    """
    st.markdown("""
    <div class="section-header" style="font-size:1.15rem; margin-top:0.5rem;">
        <span class="dot"></span>
        Bulk Inventory / Stock Update
        &nbsp;<span class="badge badge-success">Inventory API</span>
    </div>""", unsafe_allow_html=True)

    # ── Sample download ───────────────────────────────────────
    dl_col, _ = st.columns([1, 4])
    with dl_col:
        st.download_button(
            "📥 Download Sample Stock File",
            data=_to_excel(_sample_df()),
            file_name="sample_stock_update.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_sample_stock",
        )

    # ── Guard: no file uploaded ───────────────────────────────
    if stock_file is None:
        st.markdown("""
        <div class="warning-box">
            ⬆️ Upload a <strong>Stock Update file</strong> using the uploader above to get started.
        </div>""", unsafe_allow_html=True)
        return

    df_stock, ferr = load_file(stock_file)
    if ferr:
        st.error(ferr)
        return

    # ── File preview ──────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        st.markdown(f"**📄 File:** `{stock_file.name}`")
    with fc2:
        st.markdown(f"**Rows:** `{len(df_stock)}`")
    with fc3:
        st.markdown(f"**Cols:** `{len(df_stock.columns)}`")
    st.dataframe(df_stock.head(8), use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Step indicator ────────────────────────────────────────
    st.markdown("""
    <div class="steps">
        <div class="step done">① File Uploaded</div>
        <div class="step active">② Run Update</div>
        <div class="step">③ Download Report</div>
    </div>""", unsafe_allow_html=True)

    btn_col, _ = st.columns([1, 3])
    with btn_col:
        run_stock = st.button(
            "🚀 Start Stock Update", key="stock_update", use_container_width=True
        )

    if not run_stock:
        return

    # ── Validation ────────────────────────────────────────────
    if not shop_url or not access_token:
        st.error("⚠️ Enter your **Shop URL** and **Access Token** in the API Settings panel first.")
        return

    sku_stock, serr = process_stock_file(df_stock)
    if serr:
        st.error(serr)
        return
    if not sku_stock:
        st.warning("No valid stock rows found in the file.")
        return

    # ── Fetch Shopify SKUs + Location ─────────────────────────
    with st.spinner("Fetching products & inventory location from Shopify…"):
        shopify_skus, skuerr = get_skus_fn(shop_url, api_version, access_token)
        location_id, locerr  = get_shopify_location_id(shop_url, api_version, access_token)

    if skuerr:
        st.error(skuerr)
        return
    if locerr:
        st.error(locerr)
        return

    matched   = set(sku_stock.keys()) & set(shopify_skus.keys())
    unmatched = set(sku_stock.keys()) - set(shopify_skus.keys())

    m1, m2, m3 = st.columns(3)
    m1.metric("📋 File SKUs",     len(sku_stock))
    m2.metric("✅ Matched",        len(matched))
    m3.metric("❌ Not in Shopify", len(unmatched))

    if not matched:
        st.warning("No matching SKUs found between the file and Shopify.")
        return

    # ── Update progress ───────────────────────────────────────
    st.markdown("**⚡ Update Progress**")
    pbar      = st.progress(0)
    stxt      = st.empty()
    log_lines: list = []
    log_area  = st.empty()
    results   = []
    updated = errors = 0
    total = len(matched)

    for i, sku in enumerate(sorted(matched), 1):
        new_qty           = sku_stock[sku]
        inventory_item_id = shopify_skus[sku].get("inventory_item_id")

        if not inventory_item_id:
            errors += 1
            log_lines.append(f"❌  [{i:03d}]  {sku:<20}  missing inventory_item_id")
            log_area.markdown(
                "<div class='log-container'>" + "<br>".join(log_lines[-20:]) + "</div>",
                unsafe_allow_html=True,
            )
            pbar.progress(i / total)
            continue

        resp = set_inventory_level(
            shop_url, api_version, access_token,
            location_id, inventory_item_id, new_qty,
        )

        if resp.status_code == 200:
            updated += 1
            line = f"✅  [{i:03d}]  {sku:<20}  qty → {new_qty}"
            results.append({
                "S.No":             i,
                "ERP Code":          sku,
                "Updated Quantity":  new_qty,
                "Updated Date":      datetime.now().strftime("%Y-%m-%d"),
            })
        else:
            errors += 1
            line = f"❌  [{i:03d}]  {sku:<20}  HTTP {resp.status_code}"

        log_lines.append(line)
        log_area.markdown(
            "<div class='log-container'>" + "<br>".join(log_lines[-20:]) + "</div>",
            unsafe_allow_html=True,
        )
        pbar.progress(i / total)
        stxt.markdown(f"Processing **{i}** of **{total}** — {sku}")
        time.sleep(0.2)

    stxt.empty()
    pbar.progress(1.0)

    # ── Final summary ─────────────────────────────────────────
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
        out, fname = excel_download(result_df, "stock_update")
        st.download_button(
            label="📥 Download Stock Update Report",
            data=out,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
