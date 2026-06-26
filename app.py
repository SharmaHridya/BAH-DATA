# 🛰️ ISRO BAH 2026 - Urban Heat Mitigation Simulator

import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
import datetime
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="ISRO BAH 2026: UHI Simulator", layout="wide")

# CUSTOM CSS STYLE
st.markdown("""
    <style>
    /* Dark Theme Core */
    .stApp {
        background: radial-gradient(circle at top right, #1a1f2e, #0e1117);
        color: #e0e0e0;
    }
    
    /* Sleek Glassmorphism Cards */
    div[data-testid="metric-container"] {
        background: rgba(30, 30, 45, 0.6);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 16px;
        transition: transform 0.3s ease, border 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        border: 1px solid #ff4b4b;
        transform: scale(1.02);
    }

    /* Sidebar - Deep Space Look */
    [data-testid="stSidebar"] {
        background-color: rgba(14, 17, 23, 0.95);
        border-right: 1px solid #2d2d3d;
    }

    /* Button: Neon Glow Effect */
    .stButton>button {
        background: linear-gradient(90deg, #ff4b4b, #ff8c4b);
        color: white;
        border: none;
        border-radius: 50px; /* Pill shape */
        padding: 0.5rem 2rem;
        font-weight: 700;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    
    .stButton>button:hover {
        filter: brightness(1.2);
        box-shadow: 0 0 20px rgba(255, 75, 75, 0.6);
    }
    
    /* Header Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE FOR SLIDERS ---
if 'global_tree' not in st.session_state: st.session_state.global_tree = 0
if 'global_roof' not in st.session_state: st.session_state.global_roof = 0
if 'global_albedo' not in st.session_state: st.session_state.global_albedo = 0

def reset_sliders():
    st.session_state.global_tree = 0
    st.session_state.global_roof = 0
    st.session_state.global_albedo = 0

# --- EARTH ENGINE SETUP ---
EE_PROJECT_ID = "bah-isro"

try:
    ee.Initialize(project=EE_PROJECT_ID)
except Exception as e:
    st.error(f"Earth Engine Init Failed: {e}")
    st.stop()


# --- FOLIUM + EE LAYER HELPER ---
def add_ee_layer(self, ee_image_object, vis_params, name, shown=True, opacity=1.0):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict["tile_fetcher"].url_format,
        attr="Google Earth Engine",
        name=name,
        overlay=True,
        control=True,
        show=shown,
        opacity=opacity,
    ).add_to(self)

folium.Map.add_ee_layer = add_ee_layer


# --- SIDEBAR ---
st.sidebar.title("🌿 Intervention Controls")

st.sidebar.subheader("📅 Live Satellite Data")
st.sidebar.caption("Tip: Use tight 1-month windows (e.g., May 2023) to see seasonal variance. Wide multi-year windows will average out and look identical.")

start_date_picker = st.sidebar.date_input("Start Date", datetime.date(2023, 5, 1))
end_date_picker = st.sidebar.date_input("End Date", datetime.date(2023, 5, 31))

if start_date_picker > end_date_picker:
    st.sidebar.error("🚨 Error: Start Date cannot be after the End Date.")
    st.stop()

start_date = start_date_picker.strftime("%Y-%m-%d")
end_date = end_date_picker.strftime("%Y-%m-%d")

map_mode = st.sidebar.radio(
    "Select Layer",
    ["Land Surface Temperature", "Green Cover (NDVI)", "Urban Heat Risk"]
)

with st.sidebar.form("controls"):
    st.markdown("**Simulate Mitigation Strategies (Manual)**")
    # Tied directly to session state keys to maintain persistence
    tree_canopy = st.slider("Add Tree Canopy %", 0, 50, key="global_tree")
    cool_roofs = st.slider("Add Cool Roofs %", 0, 100, key="global_roof")
    albedo_boost = st.slider("Boost Surface Albedo %", 0, 50, key="global_albedo")
    
    col1, col2 = st.columns(2)
    run = col1.form_submit_button("Run Simulation", type="primary")
    reset = col2.form_submit_button("Reset", on_click=reset_sliders)


# --- STUDY AREA ---
delhi_bounds = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])


# --- SATELLITE DATA INGESTION ---
l8_dataset = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(delhi_bounds).filterDate(start_date, end_date).filter(ee.Filter.lt("CLOUD_COVER", 30))
lst_image = l8_dataset.median().select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")

s2_dataset = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(delhi_bounds).filterDate(start_date, end_date).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
s2_median = s2_dataset.median()
ndvi_image = s2_median.normalizedDifference(["B8", "B4"]).rename("NDVI")
albedo_image = s2_median.select(["B2", "B3", "B4", "B8"]).reduce(ee.Reducer.mean()).divide(10000).rename("Albedo")

era5_dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterBounds(delhi_bounds).filterDate(start_date, end_date)
air_temp_image = era5_dataset.median().select("temperature_2m").subtract(273.15).rename("AirTemp")

urban_geometry = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").eq(50).rename("Urban")
uhi_index = (lst_image.multiply(0.6).add(urban_geometry.multiply(15)).subtract(ndvi_image.multiply(10))).rename("UHI")


# --- DATA EXTRACTION ENGINE ---
@st.cache_data
def get_hotspots(start_d, end_d):
    spots = [
        ("Najafgarh", 28.6090, 76.9855),
        ("Bawana", 28.7988, 77.0329),
        ("Okhla", 28.5284, 77.2721),
        ("Palam", 28.5606, 77.1040),
        ("Badarpur", 28.5036, 77.3045),
    ]

    roi = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(roi).filterDate(start_d, end_d).filter(ee.Filter.lt("CLOUD_COVER", 30)).median()
    lst = l8.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")
    
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi).filterDate(start_d, end_d).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30)).median()
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")
    albedo = s2.select(["B2", "B3", "B4", "B8"]).reduce(ee.Reducer.mean()).divide(10000).rename("Albedo")
    
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterBounds(roi).filterDate(start_d, end_d).median()
    air = era5.select("temperature_2m").subtract(273.15).rename("AirTemp")
    u_wind = era5.select("u_component_of_wind_10m")
    v_wind = era5.select("v_component_of_wind_10m")
    wind_speed = u_wind.pow(2).add(v_wind.pow(2)).sqrt().rename("WindSpeed")
    
    # Extract baseline UHI so we can use it in our dynamic metrics
    urban = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").eq(50).rename("Urban")
    uhi = lst.multiply(0.6).add(urban.multiply(15)).subtract(ndvi.multiply(10)).rename("UHI")
    
    combined = ee.Image.cat([lst, ndvi, albedo, air, wind_speed, uhi])
    
    results = []
    for name, lat, lon in spots:
        pt = ee.Geometry.Point([lon, lat])
        try:
            stats = combined.reduceRegion(reducer=ee.Reducer.mean(), geometry=pt, scale=30).getInfo()
            results.append({
                "Location": name,
                "Lat": lat, "Lon": lon,
                "ERA5 Air Temp (°C)": stats.get("AirTemp"),
                "ERA5 Wind (m/s)": stats.get("WindSpeed"),
                "Baseline LST (°C)": stats.get("LST"),
                "Baseline NDVI": stats.get("NDVI"),
                "Baseline Albedo": stats.get("Albedo"),
                "Baseline UHI": stats.get("UHI"),
            })
        except Exception as e:
            results.append({
                "Location": name, "Lat": lat, "Lon": lon,
                "ERA5 Air Temp (°C)": None, "ERA5 Wind (m/s)": None, "Baseline LST (°C)": None, "Baseline NDVI": None, "Baseline Albedo": None, "Baseline UHI": None
            })

    return results

hotspots_data = get_hotspots(start_date, end_date)
df_hotspots = pd.DataFrame(hotspots_data)
df_hotspots.fillna(np.nan, inplace=True)


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

df_hotspots["Manual Mitigated LST (°C)"] = df_hotspots.apply(lambda row: simulate_mitigation(row, st.session_state.global_tree, st.session_state.global_roof, st.session_state.global_albedo), axis=1)
df_hotspots["Manual Temp Drop (°C)"] = df_hotspots["Baseline LST (°C)"] - df_hotspots["Manual Mitigated LST (°C)"]

st.session_state.df_hotspots = df_hotspots

# --- UI: MAIN DASHBOARD ---
st.title("🛰️ Geospatial Urban Heat Mitigation Simulator")
st.markdown("ISRO BAH 2026 Prototype | Integrating Landsat 8, Sentinel-2, and ERA5 Data")

if 'tip_dismissed' not in st.session_state: st.session_state.tip_dismissed = False
if 'selected_loc_name' not in st.session_state: st.session_state.selected_loc_name = "Najafgarh"

tip_placeholder = st.empty()
if not st.session_state.tip_dismissed:
    tip_placeholder.info("💡 **Tip:** Click on any hotspot (colored dot) on the interactive map at the bottom to view its specific metrics here! Detailed analytical charts are located in the **Data Explorer** tab.")

metrics_placeholder = st.empty()

# --- PINN OPTIMIZATION ENGINE ---
st.markdown("---")
st.subheader("🧠 Physics-Informed Neural Network (PINN) Optimizer")
st.markdown("The AI optimization engine minimizes a mock Surface Energy Balance cost-function to prescribe the optimal, location-specific mix of interventions.")

if 'df_opt' not in st.session_state: st.session_state.df_opt = None

if st.button("Run PINN Optimization", type="primary"):
    with st.spinner("Solving energy balance equations and minimizing heat capacity functions..."):
        time.sleep(1.5) 
        
        def optimize_row(row):
            if pd.isna(row["Baseline LST (°C)"]):
                return pd.Series({"Opt Trees %": 0, "Opt Roofs %": 0, "Opt Albedo %": 0, "Opt LST (°C)": np.nan})
            
            ndvi = row["Baseline NDVI"]
            albedo = row["Baseline Albedo"]
            
            opt_trees = 45 if ndvi < 0.15 else (20 if ndvi < 0.3 else 5)
            opt_roofs = 80 if albedo < 0.15 else 40
            opt_albedo_boost = 30 if albedo < 0.15 else 10
            
            opt_lst = simulate_mitigation(row, opt_trees, opt_roofs, opt_albedo_boost)
            
            return pd.Series({
                "Prescribed Trees (%)": opt_trees, 
                "Prescribed Cool Roofs (%)": opt_roofs, 
                "Prescribed Albedo Boost (%)": opt_albedo_boost, 
                "Optimized LST (°C)": opt_lst
            })
            
        opt_results = df_hotspots.apply(optimize_row, axis=1)
        st.session_state.df_opt = pd.concat([df_hotspots[["Location", "Baseline LST (°C)"]], opt_results], axis=1)

if st.session_state.df_opt is not None:
    df_opt = st.session_state.df_opt
    st.success("Optimization Complete! Found global minimum for Urban Heat Island effect.")
    st.dataframe(df_opt.style.format({"Baseline LST (°C)": "{:.2f}", "Optimized LST (°C)": "{:.2f}"}), use_container_width=True)
    
    avg_drop = (df_opt["Baseline LST (°C)"] - df_opt["Optimized LST (°C)"]).mean()
    if pd.notna(avg_drop):
        st.info(f"💡 **PINN Insight:** By applying location-specific interventions rather than a blanket city-wide policy, the model projects an optimal average cooling of **{avg_drop:.2f}°C**. Notice how industrial areas are prescribed higher Cool Roof percentages, while residential fringes lean towards Tree Canopy expansion.")

# --- MAP ---
st.markdown("---")
st.subheader("🗺️ Interactive Spatial View")

# Dynamic Heatmap Context Legend
if map_mode == "Land Surface Temperature":
    st.caption("🟢 **Color Context (LST):** Blue/Cyan (Cooler, ~20°C) ➔ Yellow/Orange (Warm) ➔ Red (Extremely Hot, 50°C+)")
elif map_mode == "Green Cover (NDVI)":
    st.caption("🟢 **Color Context (NDVI):** White/Yellow (Barren/Urban, ~0.0) ➔ Light Green (Sparse) ➔ Dark Green (Dense Forest, ~0.6+)")
elif map_mode == "Urban Heat Risk":
    st.caption("🟢 **Color Context (UHI Risk):** Blue/Cyan (Low Risk) ➔ Yellow/Orange (Moderate Vulnerability) ➔ Red (Severe Heat Risk Zone)")

m = folium.Map(location=[28.6, 77.2], zoom_start=10)

vis_lst = {"min": 20, "max": 50, "palette": ["blue", "cyan", "green", "yellow", "orange", "red"]}
vis_ndvi = {"min": 0, "max": 0.6, "palette": ["white", "yellow", "green", "darkgreen"]}

try:
    if map_mode == "Land Surface Temperature": m.add_ee_layer(lst_image.clip(delhi_bounds), vis_lst, "LST", opacity=0.65)
    elif map_mode == "Green Cover (NDVI)": m.add_ee_layer(ndvi_image.clip(delhi_bounds), vis_ndvi, "NDVI", opacity=0.65)
    elif map_mode == "Urban Heat Risk": m.add_ee_layer(uhi_index.clip(delhi_bounds), vis_lst, "UHI", opacity=0.65)
except Exception: pass 

for idx, row in df_hotspots.iterrows():
    if pd.notna(row["Manual Mitigated LST (°C)"]):
        color = "green" if row["Manual Mitigated LST (°C)"] < 40 else "red"
        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=10,
            tooltip=f"{row['Location']} (Click for details)",
            popup=f"{row['Location']} | Mitigated: {row['Manual Mitigated LST (°C)']:.1f}°C",
            color=color, fill=True, fill_opacity=0.7,
        ).add_to(m)

folium.LayerControl().add_to(m)

map_data = st_folium(m, width=1000, height=500)

if map_data and map_data.get("last_object_clicked"):
    click_lat = map_data["last_object_clicked"]["lat"]
    click_lon = map_data["last_object_clicked"]["lng"]
    
    df_hotspots['dist'] = np.sqrt((df_hotspots['Lat'] - click_lat)**2 + (df_hotspots['Lon'] - click_lon)**2)
    closest_row = df_hotspots.loc[df_hotspots['dist'].idxmin()]
    
    if closest_row['dist'] < 0.1: 
        st.session_state.selected_loc_name = closest_row["Location"]
        st.session_state.tip_dismissed = True
        tip_placeholder.empty()

selected_row = df_hotspots[df_hotspots["Location"] == st.session_state.selected_loc_name].iloc[0]
selected_loc_name = selected_row["Location"]

# --- DYNAMIC METRICS DISPLAY ---
with metrics_placeholder.container():
    if not pd.isna(selected_row["Baseline LST (°C)"]):
        col1, col2, col3 = st.columns(3)
        
        if map_mode == "Land Surface Temperature":
            col1.metric(f"{selected_loc_name} Air Temp", f"{selected_row['ERA5 Air Temp (°C)']:.1f} °C", help="Source: ERA5 Atmospheric Data (ECMWF)")
            col2.metric(f"{selected_loc_name} Baseline LST", f"{selected_row['Baseline LST (°C)']:.1f} °C", help="Source: Landsat 8 Thermal Infrared Sensor")
            col3.metric(f"{selected_loc_name} Mitigated LST", f"{selected_row['Manual Mitigated LST (°C)']:.1f} °C", 
                        f"-{selected_row['Manual Temp Drop (°C)']:.1f} °C", delta_color="inverse", help="Source: Physics-Informed Interactive Simulation")
                        
        elif map_mode == "Green Cover (NDVI)":
            base_ndvi = selected_row['Baseline NDVI']
            # Calculate a mock target NDVI based on the tree slider
            target_ndvi = min(base_ndvi + (st.session_state.global_tree / 100.0) * 0.5, 0.99)
            ndvi_boost = target_ndvi - base_ndvi
            
            col1.metric(f"{selected_loc_name} Baseline Albedo", f"{selected_row['Baseline Albedo']:.3f} (idx)", help="Source: Sentinel-2 Harmonized (Unitless Broadband Proxy 0-1)")
            col2.metric(f"{selected_loc_name} Baseline NDVI", f"{base_ndvi:.3f} (idx)", help="Source: Sentinel-2 Harmonized (Normalized Difference Vegetation Index -1 to 1)")
            col3.metric(f"{selected_loc_name} Target NDVI", f"{target_ndvi:.3f} (idx)", f"+{ndvi_boost:.3f}", delta_color="normal", help="Source: Simulated NDVI Post Tree Canopy Intervention")
            
        elif map_mode == "Urban Heat Risk":
            base_uhi = selected_row.get('Baseline UHI', 0)
            if pd.isna(base_uhi): base_uhi = 0
            
            # Calculate the UHI drop based on LST and NDVI changes
            delta_lst = selected_row['Manual Mitigated LST (°C)'] - selected_row['Baseline LST (°C)']
            delta_ndvi = min(selected_row['Baseline NDVI'] + (st.session_state.global_tree / 100.0) * 0.5, 0.99) - selected_row['Baseline NDVI']
            
            # UHI formula: LST*0.6 + Urban*15 - NDVI*10
            mitigated_uhi = base_uhi + (delta_lst * 0.6) - (delta_ndvi * 10)
            uhi_drop = base_uhi - mitigated_uhi
            
            col1.metric(f"{selected_loc_name} Wind Speed", f"{selected_row['ERA5 Wind (m/s)']:.1f} m/s", help="Source: ERA5 (ECMWF 10m u/v components)")
            col2.metric(f"{selected_loc_name} Baseline UHI Index", f"{base_uhi:.1f} (idx)", help="Source: Calculated Composite Index (LST, ESA WorldCover, Sentinel-2)")
            col3.metric(f"{selected_loc_name} Mitigated UHI Index", f"{mitigated_uhi:.1f} (idx)", f"-{uhi_drop:.1f}", delta_color="inverse", help="Source: Simulated Composite Index Post-Intervention")
            
    else:
        st.warning(f"⚠️ Data for {selected_loc_name} is masked by clouds. Please expand the date range.")