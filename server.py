# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 1
import asyncio
import sqlite3
import logging
from typing import List, Dict
import os
import json
import secrets
import httpx
import uuid
from pathlib import Path
import aiofiles
from fastapi import FastAPI, Depends, Form, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from lps22hb import LPS22HB, read_sensor
from database import build_database, DB_SCHEME

DB_DIRECTORY = Path(__file__).parent / "data"
DB_FILE = DB_DIRECTORY / "db.db"

app = FastAPI()

def _ensure_database() -> None:
    try:
        build_database(DB_FILE, DB_SCHEME)
        logging.info("Database init")
    except Exception as exception:
        logging.error(f"failed to initialize database {exception}")
        raise RuntimeError("Pi sensor system cant operate without a database!") from exception

# Init sensor on start
@app.on_event("startup")
async def startup():
    try:
        app.state.sensor = LPS22HB()
        print("LPS22HB init")
    except Exception as exception:
        logging.error(f"Sensor init failed: {exception}")

    # now for the database
    try:
        _ensure_database()
        print("Database init")
    except Exception as exception:
        raise RuntimeError(f"Could not initialize database {exception}") from exception
    # tying the app state to the database ensures it can be accessed later.
    app.state.db_path = DB_FILE
    # I use asyncio, I don't need threading for a task like this.
    # asyncio.create_task(backend_sensor_loop())
def _sync_read_sensor() -> dict:
    pressure_hpa, temperature_c = read_sensor(app.state.sensor)
    return{
        "pressure_hpa":round(pressure_hpa,2),
        "temperature_c": round(temperature_c, 2),
        "timestamp": uuid.uuid1().time,
    }


@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        return FileResponse("./static/index.html")
    except Exception as exception:
        logging.error(f"Could not serve ./static/index.html: {exception}")
        raise HTTPException(status_code=500, detail="Missing index file") from exception

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
