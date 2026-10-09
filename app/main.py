import os
import uuid
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException

from app.file_reader import read_geo_file, get_features
from app.measurements import calculate_measurements


app = FastAPI(title="Geospatial File Measurement API")

# simple in-memory storage, data is lost when the server restarts
files_db = {}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/files/")
def upload_file(file: UploadFile = File(...)):
    filename = file.filename
    if not (filename.lower().endswith(".kml") or filename.lower().endswith(".zip")):
        raise HTTPException(status_code=400, detail="Only .kml or .zip files are allowed")

    file_id = str(uuid.uuid4())
    extension = os.path.splitext(filename)[1].lower()

    # the temp folder and the saved file are deleted automatically after the "with" block
    with tempfile.TemporaryDirectory() as temp_folder:
        save_path = os.path.join(temp_folder, "upload" + extension)

        with open(save_path, "wb") as f:
            f.write(file.file.read())

        try:
            gdf = read_geo_file(save_path)
            features = get_features(gdf)
            measurements, projected_crs = calculate_measurements(gdf)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Could not process the file: " + str(e))

    files_db[file_id] = {
        "id": file_id,
        "filename": filename,
        "feature_count": len(features),
        "crs": gdf.crs.to_string(),
        "status": "COMPLETED",
        "projected_crs": projected_crs,
        "features": features,
        "measurements": measurements,
    }

    saved_file = files_db[file_id]
    return {
        "id": saved_file["id"],
        "filename": saved_file["filename"],
        "feature_count": saved_file["feature_count"],
        "crs": saved_file["crs"],
        "status": saved_file["status"],
        "features": saved_file["features"],
    }


@app.get("/api/files/{file_id}/")
def get_file_info(file_id: str):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")

    saved_file = files_db[file_id]
    return {
        "id": saved_file["id"],
        "filename": saved_file["filename"],
        "feature_count": saved_file["feature_count"],
        "crs": saved_file["crs"],
        "status": saved_file["status"],
    }


@app.get("/api/files/{file_id}/measurements/")
def get_measurements(file_id: str):
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")

    saved_file = files_db[file_id]
    return {
        "file_id": saved_file["id"],
        "projected_crs": saved_file["projected_crs"],
        "measurements": saved_file["measurements"],
    }
