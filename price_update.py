"""
price_update.py — Price Update tab UI & logic for ShopSync.
Called from app.py via render().
"""

import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from shopify_api import (
    load_file,
    process_price_file,
    update_variant_price,
    excel_download,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "ERP Code":      ["LAPTOP001", "MOUSE002", "KB003", "MON004",
                          "CHAIR005", "HEADPH006", "WEBCAM007", "DESK008"],
        "Display Price": [54999, 1299, 2499, 18999, 9999, 3499, 2799, 12999],
        "Product Name":  ["Gaming Laptop", "Wireless Mouse", "Mechanical Keyboard",
                          "4K Monitor", "Ergonomic Chair", "Noise Cancelling Headphones",
                          "HD Webcam", "Standing Desk"],
        "Category":      ["Electronics", "Accessories", "Accessories", "Electronics",
                          "Furniture", "Accessories", "Electronics", "Furniture"],
    })


def _to_excel(df: pd.DataFrame) -> BytesIO:
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf


def render(price_file, shop_url: str, api_version: str,
           access_token: str, get_skus_fn) -> None:
    """
    Render the full Price Update tab.

    Parameters
    ----------
    price_file    : Streamlit UploadedFile or None
    shop_url      : Shopify store URL (e.g. yourstore.myshopify.com)
    api_version   : e.g. '2025-04'
    access_token  : Shopify Admin API access token
    get_skus_fn   : cached callable(shop_url, api_version, access_token)
                    → (sku_map, error_msg)
    """
    st.markdown("""
    <div class="section-header" style="font-size:1.15rem; margin-top:0.5rem;">
        <span class="dot" style="background:#5c6ac4;"></span>
        Bulk Price Update
        &nbsp;<span class="badge badge-info">Shopify Admin API</span>
    </div>""", unsafe_allow_html=True)

    # ── Sample download ───────────────────────────────────────
    dl_col, _ = st.columns([1, 4])
    with dl_col:
        st.download_button(
            "📥 Download Sample Price File",
            data=_to_excel(_sample_df()),
            file_name="sample_price_update.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_sample_price",
        )

    # ── Guard: no file uploaded ───────────────────────────────
    if price_file is None:
        st.markdown("""
        <div class="warning-box">
            ⬆️ Upload a <strong>Price Update file</strong> using the uploader above to get started.
        </div>""", unsafe_allow_html=True)
        return

    df_price, ferr = load_file(price_file)
    if ferr:
        st.error(ferr)
        return

    # ── File preview ──────────────────────────────────────────
    st.markdown('<div class="card">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns([2, 1, 1])
    with fc1:
        st.markdown(f"**📄 File:** `{price_file.name}`")
    with fc2:
        st.markdown(f"**Rows:** `{len(df_price)}`")
    with fc3:
        st.markdown(f"**Cols:** `{len(df_price.columns)}`")
    st.dataframe(df_price.head(8), use_container_width=True, hide_index=True)
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
        run_price = st.button(
            "🚀 Start Price Update", key="price_update", use_container_width=True
        )

    if not run_price:
        return

    # ── Validation ────────────────────────────────────────────
    if not shop_url or not access_token:
        st.error("⚠️ Enter your **Shop URL** and **Access Token** in the API Settings panel first.")
        return

    sku_price, perr = process_price_file(df_price)
    if perr:
        st.error(perr)
        return
    if not sku_price:
        st.warning("No valid price rows found in the file.")
        return

    # ── Fetch Shopify SKUs ────────────────────────────────────
    with st.spinner("Fetching products from Shopify…"):
        shopify_skus, serr = get_skus_fn(shop_url, api_version, access_token)
    if serr:
        st.error(serr)
        return

    matched   = set(sku_price.keys()) & set(shopify_skus.keys())
    unmatched = set(sku_price.keys()) - set(shopify_skus.keys())

    m1, m2, m3 = st.columns(3)
    m1.metric("📋 File SKUs",     len(sku_price))
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
    updated = skipped = errors = 0
    total = len(matched)

    for i, sku in enumerate(sorted(matched), 1):
        new_price  = sku_price[sku]
        variant_id = shopify_skus[sku]["variant_id"]
        old_price  = shopify_skus[sku]["price"]

        if old_price == new_price:
            skipped += 1
            pbar.progress(i / total)
            stxt.markdown(f"⏭️ Skipped `{sku}` — price unchanged")
            continue

        resp = update_variant_price(
            shop_url, api_version, access_token, variant_id, new_price
        )

        if resp.status_code == 200:
            updated += 1
            line = f"✅  [{i:03d}]  {sku:<20}  ₹{old_price:>10,.2f}  →  ₹{new_price:>10,.2f}"
            results.append({
                "S.No":         i,
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
        out, fname = excel_download(result_df, "price_update")
        st.download_button(
            label="📥 Download Price Update Report",
            data=out,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
