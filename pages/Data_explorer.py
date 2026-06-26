import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Data Explorer", layout="wide")
st.title("📊 Urban Heat Data Explorer")

# --- CUSTOM CSS STYLING ---
st.markdown("""
    <style>
    /* Style the main background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Create sleek, glowing cards for the Metrics */
    div[data-testid="metric-container"] {
        background-color: #1e1e2f;
        border: 1px solid #33334d;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        border-left: 4px solid #ff4b4b; /* Accent line on the left */
        transition: all 0.3s ease;
    }
    
    /* Hover effect for metrics */
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.2);
        border-left: 4px solid #00ff00;
    }

    /* Style the sidebar */
    [data-testid="stSidebar"] {
        border-right: 1px solid #333;
    }

    /* Style the primary buttons (Run Optimization) */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

# Prevent error if page loaded before main app
if 'global_tree' not in st.session_state: st.session_state.global_tree = 0
if 'global_roof' not in st.session_state: st.session_state.global_roof = 0
if 'global_albedo' not in st.session_state: st.session_state.global_albedo = 0

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🌿 Intervention Controls")

with st.sidebar.form("controls"):
    st.markdown("**Simulate Mitigation Strategies**")
    # Using the same keys from app.py links the sliders seamlessly!
    tree_canopy = st.slider("Add Tree Canopy %", 0, 50, st.session_state.global_tree, key="global_tree")
    cool_roofs = st.slider("Add Cool Roofs %", 0, 100, st.session_state.global_roof, key="global_roof")
    albedo_boost = st.slider("Boost Surface Albedo %", 0, 50, st.session_state.global_albedo, key="global_albedo")
    run = st.form_submit_button("Run Simulation")

# --- DATA-DRIVEN PHYSICS MODEL ---
def simulate_mitigation(row, t_canopy, c_roofs, a_boost):
    base_lst = row["Baseline LST (°C)"]
    base_ndvi = row["Baseline NDVI"]
    
    if pd.isna(base_lst):
        return np.nan
    
    veg_factor = max(1.0 - (base_ndvi if pd.notna(base_ndvi) and base_ndvi > 0 else 0), 0.2)
    tree_cooling = (t_canopy / 100.0) * 4.0 * veg_factor
    roof_cooling = (c_roofs / 100.0) * 1.5
    albedo_cooling = (a_boost / 100.0) * 2.5
    
    total_cooling = tree_cooling + roof_cooling + albedo_cooling
    return max(base_lst - total_cooling, row["ERA5 Air Temp (°C)"] if pd.notna(row["ERA5 Air Temp (°C)"]) else 20.0)

# --- DYNAMIC DATA FROM APP.PY ---
if 'df_hotspots' in st.session_state:
    df_hotspots = st.session_state.df_hotspots.copy()
    
    df_hotspots["Mitigated LST (°C)"] = df_hotspots.apply(lambda row: simulate_mitigation(row, tree_canopy, cool_roofs, albedo_boost), axis=1)
    df_hotspots["Temp Drop (°C)"] = df_hotspots["Baseline LST (°C)"] - df_hotspots["Mitigated LST (°C)"]
    
    st.markdown("---")
    st.subheader("📈 Quantitative Assessment of Drivers (Live Satellite Data)")
    
    display_cols = ["Location", "ERA5 Air Temp (°C)", "ERA5 Wind (m/s)", "Baseline LST (°C)", "Baseline NDVI", "Baseline Albedo", "Mitigated LST (°C)", "Temp Drop (°C)"]
    format_dict = {
        "ERA5 Air Temp (°C)": "{:.2f}",
        "ERA5 Wind (m/s)": "{:.2f}",
        "Baseline LST (°C)": "{:.2f}",
        "Baseline NDVI": "{:.3f}",
        "Baseline Albedo": "{:.3f}",
        "Mitigated LST (°C)": "{:.2f}",
        "Temp Drop (°C)": "{:.2f}",
    }

    if 'df_opt' in st.session_state and st.session_state.df_opt is not None:
        df_opt = st.session_state.df_opt
        df_hotspots = pd.merge(df_hotspots, df_opt[["Location", "Optimized LST (°C)", "Prescribed Trees (%)", "Prescribed Cool Roofs (%)", "Prescribed Albedo Boost (%)"]], on="Location", how="left")
        display_cols.extend(["Optimized LST (°C)", "Prescribed Trees (%)", "Prescribed Cool Roofs (%)", "Prescribed Albedo Boost (%)"])
        format_dict.update({
            "Optimized LST (°C)": "{:.2f}",
            "Prescribed Trees (%)": "{:.0f}",
            "Prescribed Cool Roofs (%)": "{:.0f}",
            "Prescribed Albedo Boost (%)": "{:.0f}"
        })
        st.markdown("Live baseline data extracted dynamically, integrated with your live manual inputs **and PINN AI Optimization results**.")
    else:
        st.markdown("Live baseline data extracted dynamically from NASA/Copernicus archives, integrated with your live manual slider inputs.")

    # Create the final stylized dataframe
    final_display_df = df_hotspots[display_cols]
    st.dataframe(final_display_df.style.format(format_dict), use_container_width=True)

    # --- DOWNLOAD BUTTON WOW FACTOR ---
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')
    csv = convert_df(final_display_df)
    st.download_button(
        label="📥 Download Mitigation Strategy Report (CSV)",
        data=csv,
        file_name='isro_uhi_strategy.csv',
        mime='text/csv',
        type="primary"
    )

    st.markdown("---")
    st.subheader("📊 Scenario-Based Intervention Evaluation")
    
    if 'df_opt' in st.session_state and st.session_state.df_opt is not None:
        st.markdown("City-wide temperature comparison reflecting manual interventions chosen on this page vs. the PINN AI Optimized recommendations.")
        chart_cols = ["Location", "Baseline LST (°C)", "Mitigated LST (°C)", "Optimized LST (°C)"]
        chart_colors = ["#ff4b4b", "#00ff00", "#00aaff"] 
    else:
        st.markdown("City-wide temperature comparison reflecting manual interventions chosen on this page.")
        chart_cols = ["Location", "Baseline LST (°C)", "Mitigated LST (°C)"]
        chart_colors = ["#ff4b4b", "#00ff00"] 

    chart_data = df_hotspots[chart_cols].set_index("Location").dropna()
    if not chart_data.empty:
        st.bar_chart(chart_data, color=chart_colors)
        
else:
    st.info("👈 **Tip:** Please run the Simulator on the main page first to load the live satellite data into this explorer.")

st.markdown("---")

# --- STATIC/PRE-COMPUTED DATASETS ---
try:
    from utils.data_engine import build_dataset
    df = build_dataset()
    st.subheader("Pre-Computed Hotspot Dataset")
    st.dataframe(df)
except Exception:
    pass 

st.subheader("Vegetation vs Heat")
try:
    st.image("graphs/ndvi_vs_temp.png")
except Exception:
    st.warning("Graph image not found at 'graphs/ndvi_vs_temp.png'")

st.subheader("Anthropogenic Heat Analysis")
try:
    st.image("graphs/ah_2010_vs_2050.png")
except Exception:
    pass

st.subheader("NO2 vs Temperature")
try:
    st.image("graphs/no2_vs_temp.png")
except Exception:
    pass

st.subheader("Hotspots Anthropogenic Heat Change")
try:
    st.image("graphs/ah_hotspots_line.png")
except Exception:
    pass

st.markdown("""
### Key Insights
- **Lower NDVI → Higher surface temperature**: Areas lacking green cover trap significantly more solar radiation.
- **Higher NO₂ → Strong urban heat correlation**: Industrial hotspots and traffic corridors correlate strongly with thermal peaks.
- **Anthropogenic Heat Evolution**: Human-generated heat from AC units, factories, and vehicles is projected to increase significantly by 2050.
""")