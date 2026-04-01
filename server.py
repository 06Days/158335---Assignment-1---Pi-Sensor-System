# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 1
import asyncio
import sqlite3
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
app = FastAPI()


# Init sensor on start
@app.on_event("startup")
async def init_sensor():
    global sensor
    app.state.sensor = LPS22HB()
    print("LPS22HB init")
    # I use asyncio, I don't need threading for a task like this.
    asyncio.create_task(backend_sensor_loop())
def _sync_read_sensor() -> dict:
    pressure_hpa, temperature_c = read_sensor(sensor)
    return{
        "pressure_hpa":round(pressure_hpa,2),
        "temperature_c": round(temperature_c, 2),
        "timestamp": uuid.uuid1().time,
    }


@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse("./static/index.html")


@app.get("/sensor", response_class=JSONResponse)
async def get_sensor_data():
    data = _sync_read_sensor()
    return data
