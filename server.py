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

# for statistics predictions - a crude way of decreasing the overhead for the database
temp_sensor_cache=[]

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
        return history
    except Exception as exception:
        logger.error(f"Failed to fetch records {exception}")
    raise HTTPException(
        status_code=500,
        detail = "Could not fetch event history"
    ) from exception
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
            logging.info("Sensor data has been logged")
            temp_sensor_cache.insert(0,data)
            if len(temp_sensor_cache)>60:
                temp_sensor_cache.pop()
            # will change for configurable threshold
            analysis=analyze_data_trends(temp_sensor_cache, threshold_val=35.0)
        except Exception as exception:
            logging.error(f"Could not log sensor data {exception}")
        # 10 Second - placeholder, will become a setting
        await asyncio.sleep(10)

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
async def get_sensor_history(limit: int = 100):
    try:
        rows = fetch_history(app.state.db_path, limit=limit)
        print(f"Dbg:{len(rows)} records in DB")
        return JSONResponse(rows)
    except Exception as exception:
        logger.exception(f"Failed to fetch history: {exception}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history") from exception
# analysis endpoint for getting the current predictions
@app.get("/sensor/analysis")
async def get_analysis():
    return JSONResponse(getattr(app.state, "current_analysis", {}))

# check for a spike in temperature change, perform linear regression in order to make 'time to' predictions
async def analyze_data_trends(history: List[Dict], threshold_val: float):
    if len(history) <10:
        return{"trend":"stable","spike":False,"prediction":None}
    current_temperature=history[0]
    # assuming that the measurements are being done every second
    # It shouldn't matter, a Δtemperature that is dramatic over any period of time should be considered worthy of an alert
    past_temperature=history[5]
    delta_temperature=current_temperature-past_temperature
    is_spike = abs(delta_temperature) > 1.5 #PLACEHOLDER - Need to add to settings

    # My first linear regression experience.
    # x= index(time),y=Temperature
    number=min(len(history),30)
    y_values=[h["Temperature"] for h in history[:n]]
    x_values=list(range(n))

    average_x=sum(x_values)/number
    average_y=sum(y_values)/number

    # oh no, scary maths

    numerator = sum((x-average_x)*(y-average_y) for x,y in zip(x_values, y_values))
    denominator = sum((x-average_x)**2 for x in x_values)
    # If not able to be created, made 0
    slope=numerator/denominator if denominator !=0 else 0
    # invert it because history[0] is actually the newest
    slope=-slope
    trend = "Stable"
    if slope > 0.05: trend = "Rising"
    elif slope < -0.05: trend = "Falling"

    prediction = None

    if trend == "Rising" and current_temperature < threshold_val:
        seconds_to_hit = (threshold_val - current_temp) / slope
        prediction = round(seconds_to_hit / 60, 1) # Minutes until

    return{"trend": trend, "spike": is_spike,"prediction": prediction}



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
