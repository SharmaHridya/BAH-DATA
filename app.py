# 🛰️ ISRO BAH 2026 - Urban Heat Mitigation Simulator

import streamlit as st
import folium
from streamlit_folium import st_folium
import ee

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



# --- SIDEBAR ---
st.sidebar.title("🌿 Intervention Controls")

map_mode = st.sidebar.radio(
    "Select Layer",
    ["Land Surface Temperature", "Green Cover (NDVI)", "Urban Heat Risk"]
)

with st.sidebar.form("controls"):
    tree_canopy = st.slider("Tree Canopy %", 0, 50, 0)
    cool_roofs = st.slider("Cool Roofs %", 0, 100, 0)
    albedo = st.slider("Surface Albedo %", 0, 50, 0)
    run = st.form_submit_button("Run Simulation")


# --- STUDY AREA ---
delhi_bounds = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])


# --- DATA ---
dataset = (
    ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterBounds(delhi_bounds)
    .filterDate("2023-05-01", "2023-05-31")
    .filter(ee.Filter.lt("CLOUD_COVER", 5))
)

lst_image = (
    dataset.median()
    .select("ST_B10")
    .multiply(0.00341802)
    .add(149.0)
    .subtract(273.15)
)

s2 = (
    ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(delhi_bounds)
    .filterDate("2023-05-01", "2023-05-31")
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
)

ndvi_image = s2.median().normalizedDifference(["B8", "B4"]).rename("NDVI")

worldcover = ee.Image("ESA/WorldCover/v200").select("Map")
urban_geometry = worldcover.eq(50).rename("Urban")


uhi_index = (
    lst_image.multiply(0.6)
    .add(urban_geometry.multiply(15))
    .subtract(ndvi_image.multiply(10))
).rename("UHI")


# --- HOTSPOTS ---
def get_hotspots():
    spots = [
        ("Najafgarh", 28.6090, 76.9855),
        ("Bawana", 28.7988, 77.0329),
        ("Okhla", 28.5284, 77.2721),
        ("Palam", 28.5606, 77.1040),
        ("Badarpur", 28.5036, 77.3045),
    ]

    results = []

    for name, lat, lon in spots:
        pt = ee.Geometry.Point([lon, lat])

        val = lst_image.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=pt,
            scale=30,
        ).get("ST_B10").getInfo()

        temp = float(val) if val else 25.0

        results.append(
            {
                "name": name,
                "lat": lat,
                "lon": lon,
                "temp": temp,
            }
        )

    return results


hotspots = get_hotspots()


# --- SIMPLE PHYSICS MODEL ---
def simulate(temp):
    cooling = (tree_canopy * 0.04) + (cool_roofs * 0.02) + (albedo * 0.03)
    return max(temp - cooling, 10)


# --- UI ---
st.title("🛰️ Geospatial Urban Heat Mitigation Simulator")
st.markdown("ISRO BAH 2026 Prototype | Delhi NCR Hotspots")

col1, col2 = st.columns(2)

main_temp = hotspots[0]["temp"]
new_temp = simulate(main_temp)
diff = main_temp - new_temp

col1.metric("Baseline Temp", f"{main_temp:.1f} °C")
col2.metric("Mitigated Temp", f"{new_temp:.1f} °C", f"-{diff:.1f} °C")


# --- MAP ---
m = folium.Map(location=[28.6, 77.2], zoom_start=10)

vis_lst = {
    "min": 15,
    "max": 50,
    "palette": ["blue", "cyan", "green", "yellow", "orange", "red"],
}

vis_ndvi = {
    "min": 0,
    "max": 1,
    "palette": ["white", "yellow", "green", "darkgreen"],
}

vis_urban = {
    "min": 0,
    "max": 1,
    "palette": ["white", "red"],
}


if map_mode == "Land Surface Temperature":
    add_ee_layer(m, lst_image.clip(delhi_bounds), vis_lst, "LST")

elif map_mode == "Green Cover (NDVI)":
    add_ee_layer(m, ndvi_image.clip(delhi_bounds), vis_ndvi, "NDVI")

elif map_mode == "Urban Heat Risk":
    add_ee_layer(m, uhi_index.clip(delhi_bounds), vis_lst, "UHI")


# --- HOTSPOTS ON MAP ---
for h in hotspots:
    t = simulate(h["temp"])
    color = "green" if t < 40 else "red"

    folium.CircleMarker(
        location=[h["lat"], h["lon"]],
        radius=10,
        popup=f"{h['name']} {t:.1f}°C",
        color=color,
        fill=True,
        fill_opacity=0.7,
    ).add_to(m)


folium.LayerControl().add_to(m)

st_folium(m, width=1000, height=500)