import rasterio
import numpy as np

def load_tif(path):
    with rasterio.open(path) as src:
        data = src.read(1)
        data = np.where(data == src.nodata, np.nan, data)
    return data


def get_tiff_stats():
    tif_2010 = load_tif("data/2010.tif")
    tif_2050 = load_tif("data/2050.tif")

    return {
        "2010_mean": float(np.nanmean(tif_2010)),
        "2050_mean": float(np.nanmean(tif_2050)),
        "delta": float(np.nanmean(tif_2050) - np.nanmean(tif_2010))
    }