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

# V1 Of my DB schema for the project
DB_SCHEME = """BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "EventTypes" (
	"TypeID"	INTEGER NOT NULL,
	"Name"	TEXT,
	"Description"	TEXT,
	PRIMARY KEY("TypeID" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "SensorEvents" (
	"EventID"	INTEGER NOT NULL,
	"TypeID"	INTEGER NOT NULL,
	"RecordID"	INTEGER NOT NULL,
	PRIMARY KEY("EventID" AUTOINCREMENT),
	FOREIGN KEY("RecordID") REFERENCES "SensorRecords"("RecordID"),
	FOREIGN KEY("TypeID") REFERENCES "EventTypes"("TypeID")
);
CREATE TABLE IF NOT EXISTS "SensorRecords" (
	"RecordID"	INTEGER NOT NULL,
	"DateTime"	DateTime NOT NULL,
	"Temperature"	REAL NOT NULL,
	"Pressure"	REAL NOT NULL,
	"Humidity"	REAL NOT NULL,
	PRIMARY KEY("RecordID" AUTOINCREMENT)
);
COMMIT;
"""

def build_database(db_path: Path, schema: str) -> None:
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connect = sqlite3.connect(str(db_path))
        try:
            # Because SQL is a query language, you can pass it a string to execute!
            connect.executescript(schema)
            connect.commit()
            logging.info(f"Created database successfully at {db_path.resolve()}")
        except sqlite3.DatabaseError as db_error:
            connect.rollback()
            logging.error(f"Failed to apply schema on database: {db_error}")
            raise
        finally:
            connect.close()
    except Exception as err:
        logging.error(f"Database creation failed '{db_path}: {err}'")
        raise
app = FastAPI()


# Init sensor on start
@app.on_event("startup")
async def init_sensor():
    try:
        app.state.sensor = LPS22HB()
        print("LPS22HB init")
    except Exception as exception:
        logging.error(f"Sensor init failed: {exception}")

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


@app.get("/sensor", response_class=JSONResponse)
async def get_sensor_data():
    data = _sync_read_sensor()
    return data
