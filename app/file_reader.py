import os
import json
import zipfile

import geopandas as gpd


def find_shp_file(folder):
    for root, dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(".shp"):
                return os.path.join(root, name)
    return None


def read_geo_file(file_path):
    if file_path.lower().endswith(".zip"):
        extract_folder = file_path[:-4]
        with zipfile.ZipFile(file_path, "r") as zip_file:
            zip_file.extractall(extract_folder)

        shp_path = find_shp_file(extract_folder)
        if shp_path is None:
            raise ValueError("No .shp file found inside the zip")

        gdf = gpd.read_file(shp_path)
    else:
        gdf = gpd.read_file(file_path)

    # if the file has no CRS (for example a shapefile without .prj), assume lat/lon
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")

    return gdf


def get_features(gdf):
    if gdf.crs is not None:
        crs = gdf.crs.to_string()
    else:
        crs = None

    geojson = json.loads(gdf.to_json())

    features = []
    for index, feature in enumerate(geojson["features"]):
        geometry = feature["geometry"]

        if geometry is not None:
            geometry_type = geometry["type"]
        else:
            geometry_type = None

        features.append({
            "feature_id": index,
            "geometry_type": geometry_type,
            "geometry": geometry,
            "crs": crs,
            "properties": feature["properties"],
        })

    return features
