# 🛰️ ISRO BAH 2026 - Urban Heat Mitigation Simulator

import streamlit as st
import folium
from streamlit_folium import st_folium
import ee
import datetime
import pandas as pd
import numpy as np

st.set_page_config(page_title="ISRO BAH 2026: UHI Simulator", layout="wide")

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
    st.markdown("**Simulate Mitigation Strategies**")
    tree_canopy = st.slider("Add Tree Canopy %", 0, 50, 0)
    cool_roofs = st.slider("Add Cool Roofs %", 0, 100, 0)
    albedo_boost = st.slider("Boost Surface Albedo %", 0, 50, 0)
    run = st.form_submit_button("Run Simulation")


# --- STUDY AREA ---
delhi_bounds = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])


# --- SATELLITE DATA INGESTION (AS PER PROBLEM STATEMENT) ---

# 1. Landsat 8 (Land Surface Temperature)
l8_dataset = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(delhi_bounds).filterDate(start_date, end_date).filter(ee.Filter.lt("CLOUD_COVER", 30))
lst_image = l8_dataset.median().select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")

# 2. Sentinel-2 (Land Use / NDVI / Albedo Proxy)
s2_dataset = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(delhi_bounds).filterDate(start_date, end_date).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
s2_median = s2_dataset.median()
ndvi_image = s2_median.normalizedDifference(["B8", "B4"]).rename("NDVI")
# Broadband Albedo proxy using visible & NIR bands scaled down
albedo_image = s2_median.select(["B2", "B3", "B4", "B8"]).reduce(ee.Reducer.mean()).divide(10000).rename("Albedo")

# 3. ERA5 (Meteorological Atmospheric Temp)
era5_dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterBounds(delhi_bounds).filterDate(start_date, end_date)
air_temp_image = era5_dataset.median().select("temperature_2m").subtract(273.15).rename("AirTemp")

# 4. Urban Geometry (ESA WorldCover)
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

    # Re-declare datasets inside cached function to avoid Streamlit hash issues
    roi = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])
    l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterBounds(roi).filterDate(start_d, end_d).filter(ee.Filter.lt("CLOUD_COVER", 30)).median()
    lst = l8.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15).rename("LST")
    
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi).filterDate(start_d, end_d).filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30)).median()
    ndvi = s2.normalizedDifference(["B8", "B4"]).rename("NDVI")
    albedo = s2.select(["B2", "B3", "B4", "B8"]).reduce(ee.Reducer.mean()).divide(10000).rename("Albedo")
    
    era5 = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR").filterBounds(roi).filterDate(start_d, end_d).median()
    air = era5.select("temperature_2m").subtract(273.15).rename("AirTemp")
    
    # Combine bands to sample them all at once (Highly efficient API call)
    combined = ee.Image.cat([lst, ndvi, albedo, air])
    
    results = []
    for name, lat, lon in spots:
        pt = ee.Geometry.Point([lon, lat])
        try:
            stats = combined.reduceRegion(reducer=ee.Reducer.mean(), geometry=pt, scale=30).getInfo()
            results.append({
                "Location": name,
                "Lat": lat, "Lon": lon,
                "ERA5 Air Temp (°C)": stats.get("AirTemp"),
                "Baseline LST (°C)": stats.get("LST"),
                "Baseline NDVI": stats.get("NDVI"),
                "Baseline Albedo": stats.get("Albedo"),
            })
        except Exception as e:
            results.append({
                "Location": name, "Lat": lat, "Lon": lon,
                "ERA5 Air Temp (°C)": None, "Baseline LST (°C)": None, "Baseline NDVI": None, "Baseline Albedo": None
            })

    return results

# Fetch live data
hotspots_data = get_hotspots(start_date, end_date)
df_hotspots = pd.DataFrame(hotspots_data)

# Clean missing data (if a point was under a cloud for the entire date range)
df_hotspots.fillna(np.nan, inplace=True)


# --- DATA-DRIVEN PHYSICS MODEL ---
def simulate_mitigation(row):
    base_lst = row["Baseline LST (°C)"]
    base_ndvi = row["Baseline NDVI"]
    
    if pd.isna(base_lst):
        return np.nan
    
    # Physics Proxy: Cooling diminishes if the area is already highly vegetated (NDVI > 0.5)
    veg_factor = max(1.0 - (base_ndvi if pd.notna(base_ndvi) and base_ndvi > 0 else 0), 0.2)
    
    tree_cooling = (tree_canopy / 100.0) * 4.0 * veg_factor
    roof_cooling = (cool_roofs / 100.0) * 1.5
    albedo_cooling = (albedo_boost / 100.0) * 2.5
    
    total_cooling = tree_cooling + roof_cooling + albedo_cooling
    return max(base_lst - total_cooling, row["ERA5 Air Temp (°C)"] if pd.notna(row["ERA5 Air Temp (°C)"]) else 20.0)

df_hotspots["Mitigated LST (°C)"] = df_hotspots.apply(simulate_mitigation, axis=1)
df_hotspots["Temp Drop (°C)"] = df_hotspots["Baseline LST (°C)"] - df_hotspots["Mitigated LST (°C)"]


# --- UI: MAIN DASHBOARD ---
st.title("🛰️ Geospatial Urban Heat Mitigation Simulator")
st.markdown("ISRO BAH 2026 Prototype | Integrating Landsat 8, Sentinel-2, and ERA5 Data")

# Top Metrics for the first location (Najafgarh)
if not pd.isna(df_hotspots.iloc[0]["Baseline LST (°C)"]):
    col1, col2, col3 = st.columns(3)
    col1.metric("Najafgarh Air Temp (ERA5)", f"{df_hotspots.iloc[0]['ERA5 Air Temp (°C)']:.1f} °C")
    col2.metric("Najafgarh Baseline LST", f"{df_hotspots.iloc[0]['Baseline LST (°C)']:.1f} °C")
    col3.metric("Najafgarh Mitigated LST", f"{df_hotspots.iloc[0]['Mitigated LST (°C)']:.1f} °C", 
                f"-{df_hotspots.iloc[0]['Temp Drop (°C)']:.1f} °C", delta_color="inverse")
else:
    st.warning("⚠️ Data masked by clouds for the selected date range. Please expand the date range.")

# --- COMPREHENSIVE DATA TABLE ---
st.markdown("---")
st.subheader("📈 Quantitative Assessment of Drivers")
st.markdown("Live data extracted from NASA/Copernicus archives for selected bounding box.")
# Format dataframe for clean display
display_df = df_hotspots.drop(columns=["Lat", "Lon"]).style.format({
    "ERA5 Air Temp (°C)": "{:.2f}",
    "Baseline LST (°C)": "{:.2f}",
    "Baseline NDVI": "{:.3f}",
    "Baseline Albedo": "{:.3f}",
    "Mitigated LST (°C)": "{:.2f}",
    "Temp Drop (°C)": "{:.2f}"
})
st.dataframe(display_df, use_container_width=True)

# --- CITY-WIDE IMPACT CHART ---
st.markdown("---")
st.subheader("📊 Scenario-Based Intervention Evaluation")

chart_data = df_hotspots[["Location", "Baseline LST (°C)", "Mitigated LST (°C)"]].set_index("Location").dropna()
if not chart_data.empty:
    st.bar_chart(chart_data, color=["#ff4b4b", "#00ff00"])


# --- MAP ---
st.markdown("---")
st.subheader("🗺️ Interactive Spatial View")

m = folium.Map(location=[28.6, 77.2], zoom_start=10)

vis_lst = {"min": 20, "max": 50, "palette": ["blue", "cyan", "green", "yellow", "orange", "red"]}
vis_ndvi = {"min": 0, "max": 0.6, "palette": ["white", "yellow", "green", "darkgreen"]}

try:
    if map_mode == "Land Surface Temperature":
        m.add_ee_layer(lst_image.clip(delhi_bounds), vis_lst, "LST", opacity=0.65)
    elif map_mode == "Green Cover (NDVI)":
        m.add_ee_layer(ndvi_image.clip(delhi_bounds), vis_ndvi, "NDVI", opacity=0.65)
    elif map_mode == "Urban Heat Risk":
        m.add_ee_layer(uhi_index.clip(delhi_bounds), vis_lst, "UHI", opacity=0.65)
except Exception:
    pass 

# Plot Hotspots
for idx, row in df_hotspots.iterrows():
    if pd.notna(row["Mitigated LST (°C)"]):
        color = "green" if row["Mitigated LST (°C)"] < 40 else "red"
        folium.CircleMarker(
            location=[row["Lat"], row["Lon"]],
            radius=10,
            popup=f"{row['Location']} | Mitigated: {row['Mitigated LST (°C)']:.1f}°C",
            color=color, fill=True, fill_opacity=0.7,
        ).add_to(m)

folium.LayerControl().add_to(m)
st_folium(m, width=1000, height=500)