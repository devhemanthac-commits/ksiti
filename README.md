# KSITI - Tripartite Cadastral Reconciliation Engine

**SIH ID**: SIH26018  
**Team Name**: TEAM AROHA  
**Project Name**: KSITI  

## Team Members
- **Hemanth Kumar M**
- **Aditya PS**
- **Gurucharan NP**
- **Pramath P**
- **Amrutha M Patel**
- **Ashitha D**

---

## Overview

**KSITI** is an Intelligent Land Record Digitization & Validation Engine designed to bridge legacy paper deeds with PostGIS spatial topologies using a deterministically gated, multi-agent architecture. 

It processes handwritten/legacy land deeds, extracts relevant cadastral information, validates spatial geometries against PostGIS maps, and detects potential fraud or anomalies using machine learning.

### Core Architecture (Tripartite Pipeline)

1. **Perception Layer (Computer Vision & OCR)**
   - Leverages YOLOv8 and TrOCR (Transformers) to process uploaded image/PDF deeds.
   - Extracts handwritten text and identifies spatial bounds and property measurements.
2. **Deterministic Layer (Spatial Validation)**
   - Employs PostGIS and Shapely to cross-reference extracted deed geometries against established ground-truth mapping data.
   - Computes area variances and enforces strict statutory tolerances.
3. **Fraud Layer (Machine Learning Anomaly Detection)**
   - Utilizes Isolation Forests and localized outlier factors.
   - Flags potentially fraudulent deeds based on missing chain-of-title logic, unusual dimensional overlaps, or suspicious cryptographic signatures.

### API Endpoints

- `POST /api/v1/upload-deed`: Accepts single or multiple document files, locks them using SHA-256 cryptographic hashes, and queues them for verification.
- `GET /api/v1/document/{tracking_id}`: Retrieves the detailed JSON verification report containing the computed CIS (Cadastral Integrity Score).
- `GET /api/v1/document/{tracking_id}/image`: Streams the original uploaded document for direct visual cross-verification by reviewing officers.

---

## Tech Stack
- **Backend**: FastAPI, Python 3.11
- **Background Workers**: Celery, Redis
- **Database**: PostgreSQL with PostGIS extension (SQLite fallback for local dev)
- **Computer Vision**: OpenCV, Ultralytics (YOLOv8), EasyOCR, PyMuPDF
- **NLP / ML**: HuggingFace Transformers, Scikit-learn
- **Spatial Processing**: Shapely, GeoAlchemy2, GeoPandas

---

## Deployment (Docker)

KSITI comes with a complete, production-ready `docker-compose.yml` for simplified deployment.

1. Ensure Docker and Docker Compose are installed.
2. Build and start the services:
   ```bash
   docker-compose up -d --build
   ```
3. The API will be exposed on `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

### Included Docker Services:
- `api`: The FastAPI web server.
- `worker`: The Celery background worker.
- `db`: PostgreSQL 15 with PostGIS 3.3.
- `redis`: In-memory message broker.

---

## Local Development (No-Docker)

1. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Server**:
   ```bash
   uvicorn app.api.main:app --reload
   ```
   *Note: Without Redis or PostgreSQL configured in your environment, KSITI will automatically degrade to synchronous execution using a local SQLite database (`ksiti_local.db`).*
