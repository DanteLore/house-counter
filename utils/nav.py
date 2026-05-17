import streamlit as st

_ATTRIBUTIONS = [
    ("[OS Open UPRN](https://www.ordnancesurvey.co.uk/products/os-open-uprn)", "Ordnance Survey", "Open Government Licence"),
    ("[OS Code-Point Open](https://www.ordnancesurvey.co.uk/products/code-point-open)", "Ordnance Survey", "Open Government Licence"),
    ("[ONS Built-up Area Boundaries](https://geoportal.statistics.gov.uk/)", "Office for National Statistics", "Open Government Licence"),
    ("[Price Paid Data](https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads)", "HM Land Registry", "Open Government Licence v3.0"),
    ("[VOA 2026 Compiled Rating List](https://voaratinglists.blob.core.windows.net/html/rlidata.htm)", "Valuation Office Agency", "Open Government Licence"),
]


def render():
    c1, c2, c3, _ = st.columns([1, 1, 1, 7])
    c1.page_link("pages/0_Manage_Polygons.py", label="Polygons", icon="🗺️")
    c2.page_link("pages/1_House_Counter.py",   label="House Counter", icon="🏠")
    c3.page_link("pages/2_PricePaid.py",       label="Price Paid", icon="💷")
    st.divider()


def render_attributions():
    st.divider()
    st.caption("**Data sources**")
    for dataset, owner, licence in _ATTRIBUTIONS:
        st.caption(f"- {dataset} © {owner} — {licence}")
