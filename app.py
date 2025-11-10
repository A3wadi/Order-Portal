# CLEAN FILE HEADER (DO NOT REMOVE)
# Orders Portal (Customer Portal + Admin Page)
# UTF-8

import os
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
import streamlit as st

from db import (
    init_db,
    auth_user,
    # products
    list_products,
    upsert_product,
    delete_product,
    # fixed prices
    set_fixed_price,
    get_price_for_customer_product,
    # orders
    list_orders,
    add_order,
    add_order_line,
    list_order_lines,
    update_order_status,
    delete_order,
    # customers
    list_customers_full,
    create_customer,
    update_customer,
    # announcements
    get_active_announcements,
    create_announcement,
    deactivate_announcement,
)

# ---------------- App Config ----------------
st.set_page_config(
    page_title="Orders Portal",
    page_icon="🧾",
    layout="wide",
)

# ---------------- Helpers ----------------
def title_case_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    out.columns = [c.replace("_", " ").title() for c in df.columns]
    return out

def df_preview(df: pd.DataFrame, height: int = 280):
    if df is None or df.empty:
        st.info("No data.")
        return
    st.dataframe(title_case_cols(df), use_container_width=True, height=height)

def money(v: float) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"

def require_login() -> Dict[str, Any]:
    """Simple username/password login. Returns user dict or shows form."""
    if "user" in st.session_state and st.session_state["user"]:
        return st.session_state["user"]

    with st.form("login_form", clear_on_submit=False):
        st.subheader("Sign In")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = auth_user(username.strip(), password.strip())
        if user:
            st.session_state["user"] = user
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()

def signout_button():
    c1, c2, c3 = st.columns([1, 6, 1])
    with c3:
        if st.button("Sign out"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ---------------- Bootstrap DB ----------------
init_db()

# ---------------- Login ----------------
user = require_login()
role = user.get("role")  # "admin" or "customer"

# ---------------- Shared Header ----------------
left, mid, right = st.columns([8, 1, 2])
with left:
    if role == "admin":
        st.title("Admin Page")
    else:
        st.title("Customer Portal")
with right:
    signout_button()

st.divider()

# ---------------- Sidebar Navigation ----------------
if role == "admin":
    page = st.sidebar.radio(
        "Go to",
        ["Home", "Orders", "Catalog & Pricing (USD)", "Customers", "Announcements", "Export Tools"],
        index=0,
    )
else:
    page = st.sidebar.radio(
        "Go to",
        ["Home", "Place Order", "Track Orders", "Profile"],
        index=0,
    )

# ---------------- Announcements Widget (shared) ----------------
def show_announcements():
    ann = get_active_announcements()
    with st.expander("📣 Announcements", expanded=True):
        if not ann:
            st.info("No announcements.")
        for a in ann:
            st.markdown(f"**{a['title']}** — _{a['created_at']}_")
            st.write(a["body"])
            st.markdown("---")

# ==============================================================
# =                          ADMIN                              =
# ==============================================================

def admin_home():
    st.subheader("Dashboard (quick stats)")
    orders = list_orders()
    products = list_products()
    customers = list_customers_full()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Orders", len(orders))
    with c2:
        st.metric("Catalog Size", len(products))
    with c3:
        st.metric("Customers", len(customers))
    st.markdown("### Recent Orders")
    df_preview(pd.DataFrame(orders).sort_values("created_at", ascending=False))

def admin_orders():
    st.subheader("All Orders")
    df = pd.DataFrame(list_orders())
    df_preview(df)
    st.markdown("### Update Status")
    if not df.empty:
        oid = st.number_input("Order ID", min_value=int(df["id"].min()), step=1)
        new_status = st.selectbox("New Status", ["Draft", "Pending", "PR Generated", "Submitted", "Cancelled"])
        if st.button("Update"):
            update_order_status(int(oid), new_status)
            st.success("Updated.")
            st.rerun()
        st.markdown("### Delete Order")
        del_id = st.number_input("Delete Order ID", min_value=int(df["id"].min()), step=1, key="del_order_id")
        if st.button("Delete Order"):
            delete_order(int(del_id))
            st.warning("Order deleted.")
            st.rerun()

def admin_catalog():
    st.subheader("Add / Edit Product (USD)")
    sections = ["Chemistry", "Immunology", "Hematology"]
    analysers = ["Alinity c", "Alinity i", "Alinity HQ", "Alinity HS", "Architect c", "Architect i", "Ruby", "Emerald"]
    with st.form("add_prod"):
        c1, c2 = st.columns(2)
        with c1:
            code = st.text_input("Product Code").strip()
            name = st.text_input("Product Name / Description").strip()
            section = st.selectbox("Section", sections)
        with c2:
            analyser = st.selectbox("Analyser", analysers)
            kit_size = st.text_input("Kit Size (free text, e.g. 100T)").strip()
            default_price_usd = st.number_input("Default Price (USD)", min_value=0.0, step=1.0)
        submit = st.form_submit_button("Save Product")
    if submit:
        if not code or not name:
            st.error("Code and name are required.")
        else:
            upsert_product(code, name, section, analyser, kit_size, default_price_usd)
            st.success("Product saved.")
            st.rerun()

    st.markdown("### Catalog List")
    # Filters
    f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
    with f1:
        f_section = st.selectbox("Section", ["All"] + sections, index=0)
    with f2:
        f_an = st.selectbox("Analyser", ["All"] + analysers, index=0)
    with f3:
        f_kit = st.text_input("Kit Size (contains)").strip()
    with f4:
        q = st.text_input("Search (code or name)").strip()

    df = pd.DataFrame(list_products())
    if not df.empty:
        if f_section != "All":
            df = df[df["section"] == f_section]
        if f_an != "All":
            df = df[df["analyser"] == f_an]
        if f_kit:
            df = df[df["kit_size"].str.contains(f_kit, case=False, na=False)]
        if q:
            df = df[df["code"].str.contains(q, case=False) | df["name"].str.contains(q, case=False)]
    df_preview(df)

    st.markdown("### Delete Product")
    del_code = st.text_input("Product code to delete")
    if st.button("Delete"):
        if del_code:
            delete_product(del_code.strip())
            st.warning("Product deleted (if existed).")
            st.rerun()

    st.markdown("### Fixed Price per Customer")
    customers = list_customers_full()
    cust_names = [c["name"] for c in customers]
    products = list_products()
    prod_names = [p["name"] for p in products]
    c1, c2, c3 = st.columns(3)
    with c1:
        sel_cust = st.selectbox("Customer", cust_names) if cust_names else None
    with c2:
        sel_prod = st.selectbox("Product", prod_names) if prod_names else None
    with c3:
        price = st.number_input("Fixed Price (USD)", min_value=0.0, step=1.0)
    if st.button("Set Fixed Price"):
        if sel_cust and sel_prod:
            cid = [c for c in customers if c["name"] == sel_cust][0]["id"]
            pid = [p for p in products if p["name"] == sel_prod][0]["id"]
            set_fixed_price(cid, pid, price)
            st.success("Fixed price saved.")

def admin_customers():
    st.subheader("Create Customer")
    with st.form("create_customer"):
        c1, c2 = st.columns(2)
        with c1:
            display_name = st.text_input("Display Name").strip()
            username = st.text_input("Username").strip()
            password = st.text_input("Password").strip()
            email = st.text_input("Email").strip()
        with c2:
            phone = st.text_input("Phone").strip()
            cust_type = st.selectbox("Type", ["Direct", "GPPRR", "Tender"])
            location = st.text_input("Location").strip()
            contract_end_date = st.date_input("Contract End Date", value=None, format="YYYY-MM-DD")
            market_share_percent = st.number_input("Market Share (%)", min_value=0.0, max_value=100.0, step=1.0)
        submit = st.form_submit_button("Create")
    if submit:
        if not (display_name and username and password):
            st.error("Display name, username and password are required.")
        else:
            create_customer(
                username=username,
                password=password,
                name=display_name,
                cust_type=cust_type,
                phone=phone,
                email=email,
                location=location,
                contract_end_date=str(contract_end_date) if contract_end_date else None,
                market_share_percent=market_share_percent,
            )
            st.success("Customer created.")

    st.markdown("### Customer List & Edit")
    df = pd.DataFrame(list_customers_full())
    df_preview(df)

    if not df.empty:
        # picker
        df["display"] = df.apply(lambda r: f"{r['name']} (ID {r['id']})", axis=1)
        selection = st.selectbox("Select Customer to Edit", df["display"].tolist())
        sel_id = int(selection.split("ID")[-1].strip(" )"))

        sel = df[df["id"] == sel_id].iloc[0].to_dict()
        with st.form("edit_customer"):
            st.subheader("Edit Customer Info")
            e1, e2 = st.columns(2)
            with e1:
                e_name = st.text_input("Display Name", value=sel.get("name", ""))
                e_phone = st.text_input("Phone", value=str(sel.get("phone") or ""))
                e_type = st.selectbox("Type", ["Direct", "GPPRR", "Tender"], index=["Direct","GPPRR","Tender"].index(sel.get("type","Direct")))
                e_location = st.text_input("Location", value=str(sel.get("location") or ""))
            with e2:
                e_email = st.text_input("Email", value=str(sel.get("email") or ""))
                e_username = st.text_input("Username", value=sel.get("username",""))
                e_contract = st.text_input("Contract End Date", value=str(sel.get("contract_end_date") or ""))
                e_market = st.number_input("Market Share (%)", min_value=0.0, max_value=100.0, step=1.0, value=float(sel.get("market_share_percent") or 0.0))
            save = st.form_submit_button("Save Changes")
        if save:
            update_customer(
                sel_id,
                name=e_name,
                phone=e_phone,
                email=e_email,
                username=e_username,
                cust_type=e_type,
                location=e_location,
                contract_end_date=e_contract or None,
                market_share_percent=e_market,
            )
            st.success("Customer updated.")
            st.rerun()

def admin_announcements():
    st.subheader("Create Announcement")
    with st.form("create_announcement"):
        title = st.text_input("Title").strip()
        body = st.text_area("Body", height=120).strip()
        submit = st.form_submit_button("Publish")
    if submit:
        if not title:
            st.error("Title is required.")
        else:
            create_announcement(title, body)
            st.success("Announcement published.")

    st.markdown("### Active Announcements")
    ann = get_active_announcements()
    if not ann:
        st.info("No announcements.")
    for a in ann:
        st.markdown(f"**{a['title']}** — _{a['created_at']}_")
        st.write(a["body"])
        if st.button(f"Deactivate #{a['id']}", key=f"deact_{a['id']}"):
            deactivate_announcement(a["id"])
            st.warning("Deactivated.")
            st.rerun()
        st.divider()

def admin_export():
    st.subheader("Export Tools")
    st.caption("Download CSV snapshots.")
    prods = pd.DataFrame(list_products())
    custs = pd.DataFrame(list_customers_full())
    orders = pd.DataFrame(list_orders())
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.download_button("Download Products CSV", prods.to_csv(index=False).encode(), file_name="products.csv"):
            pass
    with c2:
        if st.download_button("Download Customers CSV", custs.to_csv(index=False).encode(), file_name="customers.csv"):
            pass
    with c3:
        if st.download_button("Download Orders CSV", orders.to_csv(index=False).encode(), file_name="orders.csv"):
            pass

# ==============================================================
# =                        CUSTOMER                             =
# ==============================================================

def customer_home():
    st.subheader(f"Hello {user.get('name','')} 👋")
    show_announcements()
    st.markdown("### Quick Start")
    st.markdown("→ Use **Place Order** to add items and submit.\n→ Track progress in **Track Orders**.")
    st.divider()

def customer_place_order():
    st.subheader("Create New Order")
    # step states
    ss = st.session_state
    ss.setdefault("cart", [])
    ss.setdefault("order_id", None)
    ss.setdefault("status", "Draft")
    sections = ["All", "Chemistry", "Immunology", "Hematology"]
    analysers = ["All", "Alinity c", "Alinity i", "Alinity HQ", "Alinity HS", "Architect c", "Architect i", "Ruby", "Emerald"]

    f1, f2, f3, f4 = st.columns([1,1,1,2])
    with f1:
        f_section = st.selectbox("Section", sections, index=0)
    with f2:
        f_an = st.selectbox("Analyser", analysers, index=0)
    with f3:
        f_kit = st.text_input("Kit Size (contains)").strip()
    with f4:
        q = st.text_input("Search (code or name)").strip()

    df = pd.DataFrame(list_products())
    if not df.empty:
        if f_section != "All":
            df = df[df["section"] == f_section]
        if f_an != "All":
            df = df[df["analyser"] == f_an]
        if f_kit:
            df = df[df["kit_size"].str.contains(f_kit, case=False, na=False)]
        if q:
            df = df[df["code"].str.contains(q, case=False) | df["name"].str.contains(q, case=False)]

    st.markdown("#### Catalog")
    if df.empty:
        st.info("No products.")
    else:
        for _, row in df.iterrows():
            with st.container(border=True):
                top = st.columns([4,1,1,1])
                with top[0]:
                    st.markdown(f"**{row['name']}**")
                    st.caption(f"{row['code']} • {row['section']} • {row['analyser']} • Kit {row['kit_size']}")
                price = get_price_for_customer_product(user["id"], int(row["id"])) or row["default_price_usd"] or 0.0
                with top[1]:
                    st.markdown("Price")
                    st.markdown(f"**{money(price)}**")
                with top[2]:
                    qty = st.number_input("Qty", min_value=0, step=1, key=f"qty_{row['id']}")
                with top[3]:
                    if st.button("Add", key=f"add_{row['id']}"):
                        if qty > 0:
                            ss["cart"].append({"product_id": int(row["id"]), "name": row["name"], "price": float(price), "qty": int(qty)})
                            st.success("Added to cart.")

    st.markdown("#### Cart")
    if not ss["cart"]:
        st.info("Cart is empty.")
    else:
        cart_df = pd.DataFrame(ss["cart"])
        cart_df["line_total"] = cart_df["price"] * cart_df["qty"]
        df_preview(cart_df, height=200)
        st.markdown(f"**Total: {money(cart_df['line_total'].sum())}**")
        if st.button("Create Order (Draft)"):
            order_id = add_order(user["id"], status="Draft")
            for item in ss["cart"]:
                add_order_line(order_id, item["product_id"], item["qty"])
            ss["order_id"] = order_id
            ss["status"] = "Draft"
            st.success(f"Order #{order_id} created.")
            ss["cart"] = []
            st.rerun()

    if ss.get("order_id"):
        st.markdown("---")
        st.markdown(f"**Current Order:** #{ss['order_id']} (Status: {ss['status']})")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Generate Purchase Request"):
                pr = f"PR-{user['id']}-{datetime.utcnow().strftime('%m%d%H%M%S')}"
                update_order_status(ss["order_id"], "PR Generated", pr_number=pr)
                ss["status"] = "PR Generated"
                st.success(f"PR generated: {pr}")
        with c2:
            if st.button("Confirm and Submit"):
                update_order_status(ss["order_id"], "Submitted")
                ss["status"] = "Submitted"
                st.success("Order submitted.")
        with c3:
            if st.button("Cancel This Order"):
                update_order_status(ss["order_id"], "Cancelled")
                st.warning("Order cancelled.")

def customer_track():
    st.subheader("Track Orders")
    df = pd.DataFrame(list_orders(customer_id=user["id"]))
    df_preview(df)

def customer_profile():
    st.subheader("Profile")
    info = {
        "Display Name": user.get("name"),
        "Type": user.get("type"),
        "Phone": user.get("phone"),
        "Email": user.get("email"),
        "Location": user.get("location"),
        "Contract End Date": user.get("contract_end_date"),
    }
    st.dataframe(pd.DataFrame([info]).T.rename(columns={0: "Value"}))
    st.info("If you need to update your profile or catalog, please contact your account manager.")

# ---------------- Page Router ----------------
if role == "admin":
    if page == "Home":
        admin_home()
    elif page == "Orders":
        admin_orders()
    elif page == "Catalog & Pricing (USD)":
        admin_catalog()
    elif page == "Customers":
        admin_customers()
    elif page == "Announcements":
        admin_announcements()
    elif page == "Export Tools":
        admin_export()
else:
    if page == "Home":
        customer_home()
    elif page == "Place Order":
        customer_place_order()
    elif page == "Track Orders":
        customer_track()
    elif page == "Profile":
        customer_profile()
