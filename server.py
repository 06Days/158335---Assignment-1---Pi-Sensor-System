# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 1
# LPS22HB is a temperature/air pressure sensor, SHTC3 is a temperature/humidity sensor.
import asyncio
import sqlite3
import logging
from typing import List, Dict, AsyncGenerator
import os
import json
import secrets
import httpx
import uuid
import datetime
from pathlib import Path
import aiofiles
from fastapi import FastAPI, Depends, Form, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import lps22hb
import shtc3
from database import build_database, DB_SCHEME, log_sensor_data, fetch_history
from starlette.responses import StreamingResponse

DB_DIRECTORY = Path(__file__).parent / "data"
DB_FILE = DB_DIRECTORY / "db.db"

app = FastAPI()

logger = logging.getLogger(__name__)

# Logging config, full Implementation
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def _ensure_database() -> None:
    try:
        build_database(DB_FILE, DB_SCHEME)
        logging.info("Database init")
    except Exception as exception:
        logging.error(f"failed to initialize database {exception}")
        raise RuntimeError("Pi sensor system cant operate without a database!") from exception
def get_records(limit: int = 100):
    try:
        history = fetch_history(DB_FILE, limit)
        if limit > 360:
            rows = gather_by_minute(history)
        return history
    except Exception as exception:
        logger.error(f"Failed to fetch records {exception}")
    raise HTTPException(
        status_code=500,
        detail = "Could not fetch event history"
    ) from exception

def group_by_minute(data: List[Dict], bucket_size_mins: int) -> List[Dict]:
    amount_buckets = {}
    for entry in data:
        dt=datetime.datetime.fromisoformat(entry["DateTime"].replace('Z',''))
        rounded_min=(dt.minute//bucket_size_mins) * bucket_size_mins
        min_key = dt.replace(minute=rounded_min, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:00Z')
        if min_key not in amount_buckets:
            amount_buckets[min_key] = {"Temperature": [], "Pressure": [], "Humidity": []}

        amount_buckets[min_key]["Temperature"].append(entry["Temperature"])
        amount_buckets[min_key]["Pressure"].append(entry["Pressure"])
        amount_buckets[min_key]["Humidity"].append(entry["Humidity"])

    grouped=[]

    for minute, values in amount_buckets.items():
        grouped.append({
            "DateTime":f"{minute}:00Z",
            "Temperature":round(sum(values["Temperature"])/len(values["Temperature"]),2),
            "Pressure":round(sum(values["Pressure"])/len(values["Pressure"]),2),
            "Humidity":round(sum(values["Humidity"])/len(values["Humidity"]),2),
        })
    return sorted(grouped, key=lambda x: x["DateTime"], reverse=True)




def _sync_read_sensor() -> dict:
    pressure_hpa, temperature_c_lps22hb = lps22hb.read_sensor(app.state.lps22hb)
    humidity_percentage, temperature_c_shtc3 = shtc3.read_sensor(app.state.shtc3)
    now=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    return{
        "DateTime": now,
        "Pressure":round(pressure_hpa,2),
        "Temperature": round(temperature_c_shtc3, 2),
        "Humidity": round(humidity_percentage, 2)
    }

async def backend_sensor_loop() -> None:
    await asyncio.sleep(1)
    while True:
        try:
            data = _sync_read_sensor()
            log_sensor_data(DB_FILE, data)
            logging.info("---")
        except Exception as exception:
            logging.error(f"Could not log sensor data {exception}")
        # 10 Second - placeholder, will become a setting
        await asyncio.sleep(1)

# Init the LPS22HB And SHTC3 sensors on start
@app.on_event("startup")
async def startup():
    try:
        app.state.lps22hb = lps22hb.LPS22HB()
        logging.info("LPS22HB init")
        app.state.shtc3 = shtc3.SHTC3()
        logging.info("SHTC3 init")
    except Exception as exception:
        logging.error(f"Sensor init failed: {exception}")
    # now for the database
    try:
        _ensure_database()
        logging.info("Database init")
    except Exception as exception:
        raise RuntimeError(f"Could not initialize database {exception}") from exception
    # tying the app state to the database ensures it can be accessed later.
    app.state.db_path = DB_FILE
    # I use asyncio, I don't need threading for a task like this.
    asyncio.create_task(backend_sensor_loop())
    logging.info("Started loggin background sensor data")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        return FileResponse("./static/index.html")
    except Exception as exception:
        logging.error(f"Could not serve ./static/index.html: {exception}")
        raise HTTPException(status_code=500, detail="Missing index file") from exception

@app.get("/sensor/history", response_class=JSONResponse)
async def get_sensor_history(minutes: int = 10):

    try:
        limit=minutes*7
        rows = fetch_history(app.state.db_path, limit=limit)
        if len(rows)<15:
            return JSONResponse(group_by_minute(rows, 1))

        if minutes==10:
            rows = group_by_minute(rows,1)
        elif minutes==60:
            rows= group_by_minute(rows,10)
        elif minutes >= 1440:
            rows = group_by_minute(rows, 60)
        # Else nothing required as rows = rows
        return JSONResponse(rows)
    except Exception as exception:
        logger.exception(f"Failed to fetch history: {exception}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history") from exception

@app.get("/sensor", response_class=JSONResponse)
async def get_sensor_data():
    try:
        data = _sync_read_sensor()
        return data
    except Exception as exception:
        logging.error(f"Could not read the sensor data {exception}")
        raise HTTPException(status_code=500, detail="Failed to read sensor data") from exception
@app.post("/sensor/log", status_code=status.HTTP_201_CREATED)
async def log_latest_sensor_data():
    try:
        data = _sync_read_sensor()
        log_sensor_data(app.state.db_path, data)
        return {"detail":"Logged sensor data"}
    except Exception as exception:
        logging.error(f"Failed to log sensor data {exception}")
        raise HTTPException(status_code=500,detail="failed to store sensor data") from exc
