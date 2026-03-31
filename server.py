# Server.py - Backend server for Assignment 1 - Toby Cammock-Elliott - 24003641
# VERSION 0

import os
import json
import secrets
import httpx
import uuid
from pathlib import Path
import aiofiles
from fastapi import FastAPI, Depends, Form, HTTPException, status, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse("./static/index.html")
