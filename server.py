# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 4
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
from fastapi.staticfiles import StaticFiles
import lps22hb
import shtc3
from database import build_database, DB_SCHEME, log_sensor_data, fetch_history, fetch_latest_event_by_name
from starlette.responses import StreamingResponse

# Alerts:
# config -> backend_sensor_loop -> index.js -> index.html

# for statistics predictions - a crude way of decreasing the overhead for the database
temp_sensor_cache=[]
CONFIG_FILE = "system.conf"
DB_DIRECTORY = Path(__file__).parent / "data"
DB_FILE = DB_DIRECTORY / "db.db"

app = FastAPI()
#for JS
app.mount("/static", StaticFiles(directory="static"), name="static")

logger = logging.getLogger(__name__)

# Logging config, full Implementation
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Our function for returning the configuration. This includes the thresholds.
def get_config():
    default_config= {
        "temp_low_thres":0.0, "temp_high_thres":40.0,
        "humid_low_thres":10.0, "humid_high_thres":90.0,
        "press_low_thres":970.0, "press_high_thres":1030.0,
        "temp_spike_amount":1.5,"humid_spike_amount":5.0,"press_spike_amount":2.0
    }
    # if it doesn't exist, we write the defaults in!

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as file:
            json.dump(default_config, file)
        return default_config

    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)
# save the new config, as adjusted in the settings menu
@app.post("/sensor/settings")
async def save_settings(request: Request):
    try:
        new_settings = await request.json()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_settings, f)
        return {"status": "success"}
    except Exception as exception:
        logging.error(f"Could not save new settings: {exception}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exception



# helper function for using the database
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

def group_by_dyn(data: List[Dict], group_seconds: int) -> List[Dict]:
    amount_buckets = {}
    for entry in data:
        try:
            dt_str=entry["DateTime"].replace('Z','')
            dt=datetime.datetime.fromisoformat(dt_str)

            ts=int(dt.timestamp())

            snapped_seconds=(ts//group_seconds) * group_seconds

            key=datetime.datetime.fromtimestamp(snapped_seconds)

            min_key = key.strftime('%Y-%m-%dT%H:%M:%S')
            if min_key not in amount_buckets:
                amount_buckets[min_key] = {"Temperature": [], "Pressure": [], "Humidity": []}

            amount_buckets[min_key]["Temperature"].append(entry["Temperature"])
            amount_buckets[min_key]["Pressure"].append(entry["Pressure"])
            amount_buckets[min_key]["Humidity"].append(entry["Humidity"])

        except Exception as exception:
            logging.error(f"Could not parse row {entry}: {exception}")
            continue

    grouped=[]

    for minute, values in amount_buckets.items():
        grouped.append({
            "DateTime":f"{minute}Z",
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
            # grab the config file (hopefully is the system.conf file)
            config=get_config();

            data = _sync_read_sensor()
            log_sensor_data(DB_FILE, data)

            alerts=[]
            # lets cast these to make that if statement tidier
            Temperature=data["Temperature"]
            Pressure=data["Pressure"]
            Humidity=data["Humidity"]
            # The backend from the alert
            if Temperature<config["temp_low_thres"] or Temperature>config["temp_high_thres"]:
                alerts.append(f"Temperature outside of range {config['temp_low_thres']}-{config['temp_high_thres']}")
            if Temperature<config["humid_low_thres"] or Temperature>config["humid_high_thres"]:
                alerts.append(f"Humidity outside of range {config['humid_low_thres']}-{config['temp_high_thres']}")
            if Temperature<config["press_low_thres"] or Temperature>config["press_high_thres"]:
                alerts.append(f"Air pressure outside of range {config['press_low_thres']}-{config['press_high_thres']}")
            app.state.current_alerts = alerts
            # temporary sensor cache gets stored here, and then popped one by one
            temp_sensor_cache.insert(0,data)
            if len(temp_sensor_cache)>60:
                temp_sensor_cache.pop()

            app.state.current_analysis = {
                "temp": analyze_data_trends(temp_sensor_cache, "Temperature", 5, config["temp_high_thres"]),
                "humid": analyze_data_trends(temp_sensor_cache, "Humidity", 5, config["humid_high_thres"]),
                "press": analyze_data_trends(temp_sensor_cache, "Pressure", 5, config["press_high_thres"])
            }
            analysis=analyze_data_trends(temp_sensor_cache, threshold_val=35.0)


        except Exception as exception:
            logging.error(f"Could not log sensor data {exception}")
        # 10 Second - placeholder, will become a setting
        await asyncio.sleep(1)

@app.get("/sensor/history/event")
async def get_event_record(name: str, limit: int = 1):
    # calls the event in database.py for returning the correct event record
    events = fetch_latest_event_by_name(app.state.db_path, limit=limit, event_name=name)
    return JSONResponse(events)

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
        limit=minutes*60

        rows = fetch_history(app.state.db_path, limit=limit)

        total_seconds=len(rows)
        if total_seconds<=60:
            return JSONResponse(rows)
        grouping=max(1,total_seconds//60)
        rows=group_by_dyn(rows,grouping)

        return JSONResponse(rows)
    except Exception as exception:
        logger.exception(f"Failed to fetch history: {exception}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history") from exception
# analysis endpoint for getting the current predictions
@app.get("/sensor/analysis")
async def get_analysis():
    return JSONResponse(getattr(app.state, "current_analysis", {}))

# check for a spike in temperature change, perform linear regression in order to make 'time to' predictions
async def analyze_data_trend(history: List[Dict], metric: str, delta_index: int, threshold_val: float):
    if len(history) < 10:
        return{"trend":"stable","spike":False,"prediction":None}

    current_value=history[0][metric]
    # assuming that the measurements are being done every second
    # It shouldn't matter, a Δvalue that is dramatic over any period of time should be considered worthy of an alert
    past_value=history[delta_index]

    config=get_config();

    delta_value=current_value-past_value
    
    spike_threshold = config["temp_spike_amount"] if metric == "Temperature" else config["humid_spike_amount"] if metric == "Humidity" else config["press_spike_amount"]
    is_spike = abs(delta_value) > spike_threshold

    # My first linear regression experience.
    # x= index(time),y=Temperature
    number=min(len(history),30)
    y_values=[h[metric] for h in history[:n]]
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
    if slope > 0.02: trend = "Rising"
    elif slope < -0.02: trend = "Falling"

    prediction = None

    if trend == "Rising" and current_value < threshold_val and slope > 0:
        seconds_to_hit = (threshold_val - current_value) / slope
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
