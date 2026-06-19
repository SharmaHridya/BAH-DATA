import streamlit as st

st.title("📊 Urban Heat Data Explorer")

from utils.data_engine import build_dataset

df = build_dataset()

st.subheader("Hotspot Dataset")
st.dataframe(df)

# --- nvdi vs heat ---
st.subheader("Vegetation vs Heat")

st.image("graphs/ndvi_vs_temp.png")

# --- anthropogenic heat ---
st.subheader("Anthropogenic Heat Analysis")
st.image("graphs/ah_2010_vs_2050.png")
st.image("graphs/ah_increase.png")

# --- no2 vs temperature ---
st.subheader("NO2 vs Temperature")
st.image("graphs/no2_vs_temp.png")


st.markdown("""
### Key Insights

- Lower NDVI → Higher surface temperature
- Higher NO₂ → Strong urban heat correlation
- Anthropogenic heat is projected to increase significantly by 2050
""")
