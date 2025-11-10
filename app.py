import streamlit as st
import pandas as pd
from db import init_db, auth_user, add_order, list_orders, list_products, add_product, delete_product

init_db()

st.set_page_config(page_title="Orders Portal", layout="wide")

# --------- تسجيل الدخول ----------
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 Login Page")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = auth_user(username, password)
        if user:
            st.session_state.user = {"username": user[1], "role": user[3]}
            st.rerun()
        else:
            st.error("Invalid username or password.")

else:
    role = st.session_state.user["role"]
    username = st.session_state.user["username"]

    st.sidebar.write(f"👤 Logged in as: **{username}** ({role})")
    if st.sidebar.button("Sign out"):
        st.session_state.user = None
        st.rerun()

    # ------------------- واجهة الأدمن -------------------
    if role == "admin":
        st.title("🧠 Admin Page")

        tab1, tab2, tab3 = st.tabs(["Products", "Orders", "Dashboard"])

        with tab1:
            st.subheader("Add Product")
            name = st.text_input("Product Name")
            analyzer = st.selectbox("Analyzer", ["Alinity C", "Alinity I", "Architect", "Other"])
            kit_size = st.number_input("Kit Size", min_value=1, step=1)
            price = st.number_input("Price ($)", min_value=0.0, step=0.5)

            if st.button("Add Product"):
                add_product(name, analyzer, kit_size, price)
                st.success("✅ Product added successfully.")

            st.divider()
            st.subheader("Product List")
            products = list_products()
            if products:
                df = pd.DataFrame(products, columns=["ID", "Name", "Analyzer", "Kit Size", "Price"])
                st.dataframe(df, use_container_width=True)

                delete_id = st.number_input("Enter Product ID to delete", min_value=0)
                if st.button("Delete Product"):
                    delete_product(delete_id)
                    st.warning(f"Product {delete_id} deleted.")
                    st.rerun()
            else:
                st.info("No products yet.")

        with tab2:
            st.subheader("Submitted Orders")
            orders = list_orders()
            df_orders = pd.DataFrame(orders, columns=["ID", "Customer", "Product", "Qty", "Status", "Created At"])
            st.dataframe(df_orders, use_container_width=True)

        with tab3:
            st.subheader("📊 Dashboard")
            orders = list_orders()
            if orders:
                df = pd.DataFrame(orders, columns=["ID", "Customer", "Product", "Qty", "Status", "Created At"])
                st.metric("Total Orders", len(df))
                st.metric("Unique Customers", df["Customer"].nunique())
            else:
                st.info("No data yet.")

    # ------------------- واجهة العميل -------------------
    else:
        st.title("📦 Customer Portal")
        products = list_products()
        if not products:
            st.warning("No products available yet.")
        else:
            df = pd.DataFrame(products, columns=["ID", "Name", "Analyzer", "Kit Size", "Price"])
            st.dataframe(df, use_container_width=True)

            product_id = st.number_input("Product ID", min_value=1)
            quantity = st.number_input("Quantity", min_value=1, step=1)

            if st.button("Place Order"):
                add_order(username, product_id, quantity)
                st.success("✅ Order submitted successfully!")

        st.divider()
        st.subheader("My Orders")
        orders = list_orders()
        df_orders = pd.DataFrame(orders, columns=["ID", "Customer", "Product", "Qty", "Status", "Created At"])
        my_orders = df_orders[df_orders["Customer"] == username]
        if not my_orders.empty:
            st.dataframe(my_orders, use_container_width=True)
        else:
            st.info("No orders yet.")
