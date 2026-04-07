# database.py - Backend SQLite database manager for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 2
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

# V2 Of my DB schema for the project - now includes eventTypes
DB_SCHEME = """
BEGIN TRANSACTION;
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
INSERT INTO "EventTypes" VALUES (1,'Highest Temperature','The highest temperature recorded by the sensor');
INSERT INTO "EventTypes" VALUES (2,'Lowest Temperature','The lowest temperature recorded by the sensor');
INSERT INTO "EventTypes" VALUES (3,'Highest Pressure','The highest air pressure recorded by the sensor');
INSERT INTO "EventTypes" VALUES (4,'Lowest Pressure','The lowest air pressure recorded by the sensor');
INSERT INTO "EventTypes" VALUES (5,'Highest Humidity','The highest humidity recorded by the sensor');
INSERT INTO "EventTypes" VALUES (6,'Lowest Humidity','The lowest humidity recorded by the sensor');
COMMIT;
"""

def log_sensor_data(db_path: Path, record: dict) -> None:
    try:
        with sqlite3.connect(str(db_path)) as cursor:
            cursor.execute("""INSERT INTO SensorRecords (DateTime, Temperature, Pressure, Humidity) VALUES (?,?,?,?)""",(record["DateTime"],record["Temperature"],record["Pressure"],record["Humidity"]),)
            cursor.commit();
            record_id=cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
            # Implementation for 'events - highest / lowest records etc goes here'



    except Exception as exception:
        logging.error(f"failed to add sensor data to database {exception}")

def fetch_history(db_path: Path, limit: int=100)->List[Dict]:
    cursor=sqlite3.connect(str(db_path))
    cursor.row_factory = sqlite3.Row
    try:
        cur=cursor.cursor()
        cur.execute("""
			SELECT Temperature, Pressure,Humidity,DateTime FROM SensorRecords WHERE DateTime >= DATETIME('now' ,'-24 hours') ORDER BY DateTime DESC LIMIT ?""", (limit,),
        )
        rows=cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        cursor.close()

# A test - future implementation
def fetch_latest_event_by_name(db_path: Path, limit: int=1, event_name: str="Highest Temperature")->List[Dict]:
	cursor=sqlite3.connect(str(db_path))
    cursor.row_factory = sqlite3.Row
	try:
        cur=cursor.cursor()
		cur.execute("""SELECT EventTypes.Name, EventTypes.Description, SensorRecords.*  FROM SensorEvents INNER JOIN EventTypes ON SensorEvents.TypeID=EventTypes.TypeID INNER JOIN SensorRecords ON SensorEvents.RecordID=SensorRecords.RecordID WHERE EventTypes.name=? ORDER BY DateTime DESC LIMIT ?""", (event_name,limit),)
        rows=cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        cursor.close()



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
