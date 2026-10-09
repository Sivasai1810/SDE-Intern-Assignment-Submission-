def convert_to_projected_crs(gdf):
    # lat/lon degrees can't be used for area or length, so we convert to UTM (meters)
    if gdf.crs.is_geographic:
        utm_crs = gdf.estimate_utm_crs()
        gdf = gdf.to_crs(utm_crs)
    return gdf


def calculate_measurements(gdf):
    projected_gdf = convert_to_projected_crs(gdf)
    projected_crs = projected_gdf.crs.to_string()

    measurements = []
    for index, geometry in enumerate(projected_gdf.geometry):
        result = {
            "feature_id": index,
            "geometry_type": None,
            "area_sq_m": None,
            "length_m": None,
            "message": None,
        }

        if geometry is None or geometry.is_empty:
            result["message"] = "Feature has no geometry"
        else:
            geometry_type = geometry.geom_type
            result["geometry_type"] = geometry_type

            if geometry_type == "Polygon" or geometry_type == "MultiPolygon":
                result["area_sq_m"] = round(geometry.area, 2)
            elif geometry_type == "LineString" or geometry_type == "MultiLineString":
                result["length_m"] = round(geometry.length, 2)
            elif geometry_type == "Point" or geometry_type == "MultiPoint":
                result["message"] = "No measurement needed for points"
            else:
                result["message"] = "Measurement not supported for " + geometry_type

        measurements.append(result)

    return measurements, projected_crs
