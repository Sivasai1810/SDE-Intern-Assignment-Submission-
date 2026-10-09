# Geospatial File Measurement API

A small backend service built with **FastAPI**. You upload a geospatial file (KML or a zipped Shapefile), and it reads every feature in the file and calculates:

- **Area** for polygons
- **Length** for lines

Points are listed but not measured.

---

## Setup

You need **Python 3.10 or newer** (I used Python 3.13).

**1. Clone the repo**

```bash
git clone <your-repo-url>
cd assignment-1
```

**2. Create a virtual environment and activate it**

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Mac / Linux:
```bash
source venv/bin/activate
```

**3. Install the libraries**

```bash
pip install -r requirements.txt
```

**4. Start the server**

```bash
uvicorn app.main:app --reload
```

The server runs at `http://127.0.0.1:8000`.

The easiest way to try it is the built-in docs page: **http://127.0.0.1:8000/docs**. There you can upload a file and call every endpoint from the browser.

Two sample files are included in the `sample_data/` folder:

| File | What's inside |
|---|---|
| `sample.kml` | 1 Point, 1 LineString, 1 Polygon |
| `fields.zip` | A Shapefile with 2 Polygons |

---

## API

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/health` | Checks that the server is running |
| POST | `/api/files/` | Uploads a file and processes it |
| GET | `/api/files/{id}/` | Returns info about an uploaded file |
| GET | `/api/files/{id}/measurements/` | Returns measurements for each feature |

### 1. Upload a file

```
POST /api/files/
```

Send the file as form data with the field name `file`. Only `.kml` and `.zip` files are accepted.

**Example request**

```bash
curl -F "file=@sample_data/sample.kml" http://127.0.0.1:8000/api/files/
```

**Example response** (shortened to one feature)

```json
{
  "id": "6e222c8d-ebbd-408f-a0fe-ed2252c6c2e7",
  "filename": "sample.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "features": [
    {
      "feature_id": 2,
      "geometry_type": "Polygon",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[78.47, 17.37], [78.48, 17.37], [78.48, 17.38], [78.47, 17.38], [78.47, 17.37]]]
      },
      "crs": "EPSG:4326",
      "properties": { "Name": "Park", "category": "green" }
    }
  ]
}
```

Save the `id` from the response. You need it for the next two endpoints.

### 2. Get file info

```
GET /api/files/{id}/
```

**Example request**

```bash
curl http://127.0.0.1:8000/api/files/6e222c8d-ebbd-408f-a0fe-ed2252c6c2e7/
```

**Example response**

```json
{
  "id": "6e222c8d-ebbd-408f-a0fe-ed2252c6c2e7",
  "filename": "sample.kml",
  "feature_count": 3,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

### 3. Get measurements

```
GET /api/files/{id}/measurements/
```

**Example request**

```bash
curl http://127.0.0.1:8000/api/files/6e222c8d-ebbd-408f-a0fe-ed2252c6c2e7/measurements/
```

**Example response**

```json
{
  "file_id": "6e222c8d-ebbd-408f-a0fe-ed2252c6c2e7",
  "projected_crs": "EPSG:32644",
  "measurements": [
    {
      "feature_id": 0,
      "geometry_type": "Point",
      "area_sq_m": null,
      "length_m": null,
      "message": "No measurement needed for points"
    },
    {
      "feature_id": 1,
      "geometry_type": "LineString",
      "area_sq_m": null,
      "length_m": 2598.19,
      "message": null
    },
    {
      "feature_id": 2,
      "geometry_type": "Polygon",
      "area_sq_m": 1177298.91,
      "length_m": null,
      "message": null
    }
  ]
}
```

- `area_sq_m` is in square meters.
- `length_m` is in meters.
- `projected_crs` is the coordinate system used for the calculation.

### Errors

| Situation | Status | Message |
|---|---|---|
| Wrong file type (e.g. `.txt`) | 400 | `Only .kml or .zip files are allowed` |
| Broken file, or a zip with no `.shp` inside | 400 | `Could not process the file: ...` |
| Unknown file id | 404 | `File not found` |

---

## Architecture

### Application structure

```
assignment-1/
├── app/
│   ├── main.py           # API endpoints and in-memory storage
│   ├── file_reader.py    # Reads KML / Shapefile and extracts features
│   └── measurements.py   # CRS conversion and area / length calculation
├── sample_data/          # Example files for testing
├── requirements.txt
└── README.md
```

Each file has one job:
- `main.py` handles the HTTP side: receiving files and returning JSON.
- `file_reader.py` handles reading files.
- `measurements.py` handles the math.

### File-processing flow

1. The user uploads a file to `POST /api/files/`.
2. The file extension is checked. Only `.kml` and `.zip` are allowed.
3. The file is saved into a **temporary folder**.
4. If it is a `.zip`, it is unzipped and the `.shp` file inside is found.
5. GeoPandas reads the file into a GeoDataFrame.
6. For each feature, we collect its ID, geometry type, geometry, CRS and properties.
7. Measurements are calculated (see below).
8. Everything is saved in memory under a new random ID.
9. The temporary folder is deleted automatically.

### Measurement calculation flow

1. The geometries are converted to a projected CRS that uses meters (see CRS handling below).
2. Each feature is checked by its geometry type:

| Geometry type | What we calculate |
|---|---|
| Polygon, MultiPolygon | Area (square meters) |
| LineString, MultiLineString | Length (meters) |
| Point, MultiPoint | Nothing (a message says no measurement is needed) |
| Anything else | Nothing (a message says the type is not supported) |
| Empty or missing geometry | Nothing (a message says the feature has no geometry) |

Unsupported or empty geometries never crash the API. They just get a message.

### CRS handling

Most KML and many Shapefiles store coordinates as **latitude/longitude in degrees** (EPSG:4326). You can't calculate area or distance directly in degrees, because one degree of longitude is a different length depending on where you are on Earth.

So before measuring:

1. If the file's CRS is geographic (lat/lon), the data is converted to a **UTM zone**. UTM is a projected CRS that works in meters.
2. The right UTM zone is picked automatically with GeoPandas' `estimate_utm_crs()`, based on where the data is. For example, data around Hyderabad, India uses `EPSG:32644` (UTM zone 44N).
3. If the file is already in a projected CRS, it is used as it is.
4. If the file has no CRS at all (for example, a Shapefile without a `.prj` file), it is **assumed to be EPSG:4326**.

---

## Design Decisions

**FastAPI instead of Django**
FastAPI is lighter and needs much less setup for a small API like this. It also gives free interactive docs at `/docs`, which makes testing easy. Django + DRF would be a better fit if we needed an admin panel, users or a full database from the start.

**GeoPandas for reading files**
GeoPandas can read both KML and Shapefile with the same `read_file()` call, and it also handles CRS conversion. The alternative was reading each format by hand (an XML parser for KML, `pyshp` for Shapefiles), which would be more code and more bugs.

**Temporary files instead of keeping uploads**
GeoPandas needs a real file on disk, especially for Shapefiles, which are several files (`.shp`, `.shx`, `.dbf`, `.prj`) that must sit together. The upload is saved into a temporary folder that Python deletes automatically, even if processing fails. Nothing piles up on the server.

**UTM for measurements**
UTM is simple, widely used and accurate to within about 0.1% inside a zone. I compared my results with a geodesic calculation (pyproj `Geod`, which measures directly on the Earth's ellipsoid). The difference was around 0.05%–0.1% on the sample files. The alternative was to calculate geodesic area and length directly, which is more accurate everywhere but less common and a bit harder to read.

**One UTM zone per file**
The whole file is converted to one UTM zone, picked from the file's overall location. This is simple and fine for normal survey files that cover a city or region. It is less accurate for files that cover a very large area (see Future Scope).

**Processing during upload**
The file is processed right away in the upload request, so the status is always `COMPLETED` once you get a response. For small and medium files this is fast. Very large files would need background processing.

**In-memory storage**
Results are stored in a Python dictionary. This keeps the project simple with no database setup. The downside is that all data is lost when the server restarts.

**Assume EPSG:4326 when CRS is missing**
KML always uses EPSG:4326, and most Shapefiles without a `.prj` file are also lat/lon. Assuming EPSG:4326 lets these files still work instead of failing. The risk is that if such a file is actually in another CRS, the measurements will be wrong.

---

## Learnings

- Learned how geospatial files are structured, especially that a Shapefile is really a group of files, not just one.
- Understood why you can't measure area in lat/lon degrees, and how projected coordinate systems like UTM solve this.
- Got hands-on with GeoPandas, Shapely and pyproj for reading, converting and measuring geometries.
- Learned how to build file-upload APIs in FastAPI and handle bad input without crashing.
- Learned to check results against an independent calculation instead of just trusting the output.

---

## Future Scope

- **Database storage**: save results in PostgreSQL + PostGIS so data survives restarts.
- **Background processing**: process large files in the background (e.g. Celery or FastAPI background tasks) and update the status from `PROCESSING` to `COMPLETED` or `FAILED`.
- **Better accuracy for large areas**: pick a UTM zone per feature, or use geodesic calculations, so files that span many zones stay accurate.
- **More formats**: support GeoJSON, GeoPackage and KMZ.
- **More measurements**: polygon perimeter, and area in hectares or acres.
- **Tests**: add automated tests with `pytest` for each endpoint and edge case.
- **Limits and security**: limit upload size and check zip contents before extracting.
- **Docker**: add a Dockerfile so the project runs the same everywhere.
