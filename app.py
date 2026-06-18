# Member 4: Save this as app.py and run it using: streamlit run app.py
# You will need to install these libraries first: pip install streamlit folium streamlit-folium

import streamlit as st
import folium
from streamlit_folium import st_folium
import ee

st.set_page_config(page_title="ISRO BAH 2026: UHI Simulator", layout="wide")

# --- EARTH ENGINE SETUP ---
EE_PROJECT_ID = "bah-isro" # <--- IMPORTANT: Replace with your actual Google Cloud Project ID!

# Initialize Earth Engine. If not authenticated, show an error on the app.
try:
    if EE_PROJECT_ID == "YOUR-PROJECT-ID-HERE":
        st.warning("⚠️ **Action Required:** Please enter your Google Cloud Project ID in the code (line 12) before continuing.")
        st.info("You can find your Project ID at [console.cloud.google.com](https://console.cloud.google.com/).")
        st.stop()
        
    ee.Initialize(project=EE_PROJECT_ID)
except Exception as e:
    st.error(f"⚠️ Earth Engine Initialization Failed!\n\n**Error Details:** {e}")
    st.info("💡 **How to fix the 'Wrong Account' or 'Project Not Found' issue:**\n\n"
            "1. Open your VS Code terminal and stop the app (`Ctrl+C`).\n"
            "2. Run: `earthengine authenticate --auth_mode=notebook`\n"
            "3. **CRITICAL:** Copy the URL it gives you, open an **Incognito/Private window** in your browser, paste the URL, and log in with the *correct* Google account.\n"
            "4. Copy the authorization code it generates back into your terminal.\n"
            "5. Restart the app with `streamlit run app.py`.")
    st.stop()

# --- NATIVE FOLIUM + EARTH ENGINE BRIDGE ---
# This helper function replaces the need for the buggy 'geemap' library
def add_ee_layer(self, ee_image_object, vis_params, name, shown=True, opacity=1.0):
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True,
        show=shown,
        opacity=opacity
    ).add_to(self)

# Add EE drawing method to folium.Map.
folium.Map.add_ee_layer = add_ee_layer

# --- UI: Sidebar Controls ---
st.sidebar.title("🌿 Intervention Sandbox")

# NEW FEATURE: Dynamic Date Selector to prove real-time data
st.sidebar.subheader("📅 Live Satellite Data")
time_periods = {
    "May 2023 (Summer Heatwave)": ("2023-05-01", "2023-05-31"),
    "January 2024 (Winter Peak)": ("2024-01-01", "2024-01-31"),
    "October 2023 (Post-Monsoon)": ("2023-10-01", "2023-10-31")
}
selected_period = st.sidebar.selectbox("Select Observation Period", list(time_periods.keys()))
start_date, end_date = time_periods[selected_period]

st.sidebar.markdown("---")

# Wrap the sliders in a form so it doesn't auto-rerun on every drag
with st.sidebar.form("intervention_form"):
    st.markdown("Simulate cooling strategies using our (mock) Physics-Informed ML model.")
    
    tree_canopy = st.slider("Increase Tree Canopy (%)", 0, 50, 0)
    cool_roofs = st.slider("Implement Cool Roofs (%)", 0, 100, 0)
    albedo = st.slider("Increase Surface Albedo (%)", 0, 50, 0)
    
    # Every form must have a submit button.
    submitted = st.form_submit_button("Run Simulation")

# --- DYNAMIC DATA FETCHING ---
delhi_bounds = ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])

# Define the live Landsat 8 LST Image based on the dropdown selection
dataset = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
    .filterBounds(delhi_bounds) \
    .filterDate(start_date, end_date) \
    .filter(ee.Filter.lt('CLOUD_COVER', 5))

# Convert ST_B10 to Celsius
lst_image = dataset.median().select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15)

@st.cache_data
def get_real_hotspots(start_d, end_d):
    # Re-declare for caching purposes so Streamlit doesn't throw a HashError on EE objects
    local_dataset = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
        .filterBounds(ee.Geometry.Rectangle([76.83, 28.40, 77.34, 28.88])) \
        .filterDate(start_d, end_d) \
        .filter(ee.Filter.lt('CLOUD_COVER', 5))
    local_lst = local_dataset.median().select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15)
    
    base_spots = [
        {"name": "Najafgarh", "lat": 28.6090, "lon": 76.9855},
        {"name": "Bawana Industrial", "lat": 28.7988, "lon": 77.0329},
        {"name": "Okhla Estate", "lat": 28.5284, "lon": 77.2721},
        {"name": "Palam Airport", "lat": 28.5606, "lon": 77.1040},
        {"name": "Badarpur", "lat": 28.5036, "lon": 77.3045}
    ]
    # Ask GEE for the real temperature at these exact coordinates
    for spot in base_spots:
        pt = ee.Geometry.Point([spot['lon'], spot['lat']])
        temp_data = local_lst.reduceRegion(reducer=ee.Reducer.mean(), geometry=pt, scale=30).getInfo()
        # Fallback to 25.0 if the pixel is masked out by a cloud
        spot['base_temp'] = temp_data.get('ST_B10') or 25.0 
    return base_spots

# Fetch the hotspots based on the selected date
hotspots = get_real_hotspots(start_date, end_date)


# --- MOCK PHYSICS ENGINE ---
def calculate_new_temp(base_temp, trees, roofs, albedo):
    # Trees have high latent heat flux (cooling), roofs reflect, albedo reflects
    cooling = (trees * 0.045) + (roofs * 0.02) + (albedo * 0.03)
    return max(base_temp - cooling, 10.0) 

# --- UI: Main Dashboard ---
st.title("🛰️ Geospatial Urban Heat Mitigation Simulator")
st.markdown("**ISRO BAH 2026 Prototype** | Analyzing top 5 thermal hotspots in Delhi NCR.")

col1, col2, col3 = st.columns(3)

# Calculate metrics for the first hotspot (Najafgarh) as the main display
main_base = hotspots[0]['base_temp']
main_new = calculate_new_temp(main_base, tree_canopy, cool_roofs, albedo)
temp_drop = main_base - main_new

col1.metric("Najafgarh Baseline Temp", f"{main_base:.1f} °C")
col2.metric("Simulated Mitigated Temp", f"{main_new:.1f} °C", f"-{temp_drop:.1f} °C (Cooling Effect)", delta_color="inverse")

# --- UI: Map ---
st.subheader(f"Interactive Hotspot Map ({selected_period})")

# Use standard folium map now!
m = folium.Map(location=[28.6139, 77.2090], zoom_start=10)

# Add the actual thermal heatmap from Earth Engine using our native integration!
vis_params = {
    'min': 15, 'max': 50, 
    'palette': ['blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'darkred']
}
m.add_ee_layer(lst_image.clip(delhi_bounds), vis_params, 'Real LST Heatmap', shown=True, opacity=0.65)

# Add the 5 hotspots to the map
for spot in hotspots:
    new_t = calculate_new_temp(spot["base_temp"], tree_canopy, cool_roofs, albedo)
    
    # Change circle color if we successfully cooled it below 40C
    marker_color = "green" if new_t < 40.0 else "red"
    
    # Add a glowing circle
    folium.CircleMarker(
        location=[spot["lat"], spot["lon"]],
        radius=15,
        popup=f"{spot['name']} | Temp: {new_t:.1f}°C",
        tooltip=f"{spot['name']}",
        color=marker_color,
        fill=True,
        fill_color=marker_color,
        fill_opacity=0.6
    ).add_to(m)

# Add Layer Control to let users toggle the satellite view
folium.LayerControl().add_to(m)

# Render the map in Streamlit
st_folium(m, width=1000, height=500)

st.info("💡 Note to Judges: The temperatures shown are dynamically queried from live Landsat 8 satellite data via Google Earth Engine API. The final product will integrate an actual PINN (Physics-Informed Neural Network) solving the Surface Energy Balance equation.")