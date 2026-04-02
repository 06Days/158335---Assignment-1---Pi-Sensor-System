# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 1
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
from lps22hb import LPS22HB, read_sensor
from database import build_database, DB_SCHEME, log_sensor_data
from starlette.responses import StreamingResponse

DB_DIRECTORY = Path(__file__).parent / "data"
DB_FILE = DB_DIRECTORY / "db.db"

app = FastAPI()

async def sensor_streamer():
    while True:
        data = _sync_read_sensor()
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(2)

def _ensure_database() -> None:
    try:
        build_database(DB_FILE, DB_SCHEME)
        logging.info("Database init")
    except Exception as exception:
        logging.error(f"failed to initialize database {exception}")
        raise RuntimeError("Pi sensor system cant operate without a database!") from exception

def _sync_read_sensor() -> dict:
    pressure_hpa, temperature_c = read_sensor(app.state.sensor)
    return{
        "DateTime": datetime.datetime.utcnow().isoformat(),
        "pressure_hpa":round(pressure_hpa,2),
        "temperature_c": round(temperature_c, 2),
        "timestamp": uuid.uuid1().time,
    }

async def backend_sensor_loop() -> None:
    while True:
        try:
            data = _sync_read_sensor()
            log_sensor_data(DB_FILE, data)
            logging.info("Sensor data has been logged")
        except Exception as exception:
            logging.error(f"Could not log sensor data {exception}")
        # 10 Second - placeholder, will become a setting
        await asyncio.sleep(10)

# Init sensor on start
@app.on_event("startup")
async def startup():
    try:
        app.state.sensor = LPS22HB()
        logging.info("LPS22HB init")
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
@app.get("/sensor/stream", response_class=StreamingResponse)
async def stream_sensor_data():
    return StreamingResponse(
        sensor_streamer(),
        media_type="text/event-stream"
    )

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
