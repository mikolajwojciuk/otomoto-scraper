import streamlit as st


st.set_page_config(
    page_title="Otomoto analytics",
    page_icon="🚗",
)

st.title("Otomoto analytics")
st.subheader("Get insights from Otomoto")

st.divider()

col1, col2 = st.columns([0.28, 0.75])

col1.text(
    """Select car brand to see
insights about it

You can also specify model
to get insights about it as well
          """
)

col2.selectbox(
    label="Choose brand",
    options=["Abarth", "Audi", "Opel", "Toyota"],
    index=None,
    placeholder="Choose brand",
    label_visibility="collapsed",
)
col2.selectbox(
    label="Choose model",
    options=["All", "Punto", "A3", "A8", "535i"],
    index=0,
    placeholder="Choose model",
    label_visibility="collapsed",
)
