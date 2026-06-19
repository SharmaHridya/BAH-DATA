import pandas as pd
import streamlit as st


EE_PROJECT_ID = "bah-isro"
MODIS_LST_COLLECTION = "MODIS/061/MOD11A1"
LST_BAND = "LST_Day_1km"
START_DATE = "2024-01-01"
END_DATE = "2024-01-31"


HOTSPOTS = [
    {"Location": "Najafgarh", "Latitude": 28.6090, "Longitude": 76.9855},
    {"Location": "Bawana", "Latitude": 28.7988, "Longitude": 77.0329},
    {"Location": "Okhla", "Latitude": 28.5284, "Longitude": 77.2721},
    {"Location": "Palam", "Latitude": 28.5606, "Longitude": 77.1040},
    {"Location": "Badarpur", "Latitude": 28.5036, "Longitude": 77.3045},
]


@st.cache_data
def build_dataset() -> pd.DataFrame:
    import ee

    try:
        ee.Initialize(project=EE_PROJECT_ID)
    except Exception:
        ee.Initialize()

    image = (
        ee.ImageCollection(MODIS_LST_COLLECTION)
        .filterDate(START_DATE, END_DATE)
        .select(LST_BAND)
        .median()
    )

    rows = []
    for hotspot in HOTSPOTS:
        point = ee.Geometry.Point(
            [hotspot["Longitude"], hotspot["Latitude"]]
        )
        raw_value = (
            image.reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=1000,
            )
            .get(LST_BAND)
            .getInfo()
        )
        temperature = None

        if raw_value is not None:
            temperature = float(raw_value) * 0.02 - 273.15
        else:
            temperature = None

        rows.append(
            {
                "Location": hotspot["Location"],
                "Latitude": hotspot["Latitude"],
                "Longitude": hotspot["Longitude"],
                "Temperature": temperature,
            }
        )

    return pd.DataFrame(
        rows,
        columns=["Location", "Latitude", "Longitude", "Temperature"],
    )
