🛰️ Geospatial Urban Heat Mitigation Simulator

ISRO BAH 2026 Prototype

An interactive geospatial decision-support platform that identifies urban heat island (UHI) hotspots using satellite-derived land surface temperature data and allows users to simulate the impact of various heat mitigation strategies.

⸻

📌 Problem Statement

Rapid urbanization has led to the formation of Urban Heat Islands (UHIs), where built-up regions experience significantly higher temperatures than surrounding areas. Elevated temperatures increase energy consumption, worsen air quality, and negatively impact public health.

This project aims to leverage satellite observations and geospatial analytics to:

* Detect urban heat hotspots.
* Visualize temperature distribution across Delhi NCR.
* Analyze vegetation cover using NDVI.
* Simulate the cooling effects of sustainable interventions.
* Support data-driven urban planning decisions.

⸻

🚀 Features

🔥 Live Land Surface Temperature Mapping

* Uses Google Earth Engine and Landsat 8 imagery.
* Retrieves real satellite-derived thermal observations.
* Supports multiple observation periods for comparison.

🌳 Green Cover Visualization (NDVI)

* Uses Sentinel-2 satellite imagery.
* Calculates and displays the Normalized Difference Vegetation Index (NDVI).
* Highlights vegetation density across the study area.

📍 Hotspot Identification

Monitors major thermal hotspots in Delhi NCR:

* Najafgarh
* Bawana Industrial Area
* Okhla Industrial Estate
* Palam Airport Region
* Badarpur

🌿 Intervention Sandbox

Simulate mitigation strategies including:

* Increased Tree Canopy Coverage
* Cool Roof Adoption
* Surface Albedo Enhancement

The simulator estimates temperature reduction using a simplified physics-inspired model.

🗺️ Interactive Geospatial Dashboard

* Built with Streamlit and Folium.
* Layer switching between:
    * Land Surface Temperature
    * Green Cover (NDVI)
* Interactive hotspot markers and visual overlays.

⸻

🛠️ Technology Stack

Component	Technology
Frontend	Streamlit
Mapping	Folium
Satellite Data	Google Earth Engine
Thermal Data	Landsat 8 Collection 2 Level 2
Vegetation Data	Sentinel-2 SR Harmonized
Language	Python

⸻

📂 Project Structure

project/
│
├── app.py
├── requirements.txt
└── README.md

⸻

⚙️ Installation

Clone the Repository

git clone <repository-url>
cd <repository-name>

Create a Virtual Environment

python3 -m venv venv
source venv/bin/activate

Install Dependencies

pip install -r requirements.txt

or

pip install streamlit folium streamlit-folium earthengine-api

⸻

🌍 Google Earth Engine Setup

Authenticate Earth Engine:

earthengine authenticate

Initialize your Google Cloud Project and update:

EE_PROJECT_ID = "your-project-id"

inside app.py.

⸻

▶️ Running the Application

streamlit run app.py

The application will open in your browser automatically.

⸻

📊 Data Sources

Landsat 8 Collection 2 Level 2

Used for:

* Surface Temperature Estimation
* Urban Heat Island Analysis

Sentinel-2 SR Harmonized

Used for:

* NDVI Computation
* Green Cover Assessment

⸻

🔬 Future Enhancements

* Physics-Informed Neural Network (PINN) integration.
* Real-time weather data assimilation.
* Building density and impervious surface analysis.
* Population vulnerability assessment.
* Predictive heat-risk forecasting.
* Multi-city scalability across India.

⸻

👥 Team

Developed as part of ISRO BAH 2026.

Contributors:

* Hridya Sharma
* Team Members

⸻

📜 Disclaimer

This prototype demonstrates the integration of geospatial intelligence, satellite observations, and intervention modeling for urban heat mitigation. The current cooling simulation uses a simplified model and will be replaced by a full Physics-Informed Neural Network (PINN) framework in future iterations.