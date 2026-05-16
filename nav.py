import streamlit as st


def render():
    c1, c2, _ = st.columns([1, 1, 8])
    c1.page_link("app.py", label="House Counter", icon="🏠")
    c2.page_link("pages/1_Price_Paid.py", label="Price Paid", icon="💷")
    st.divider()
