import os
import json
import asyncio
import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

# THIS IS THE FIX: Allow the frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your specific frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class Envelope(BaseModel):
    id: str
    payload: Dict[str, Any]

async def get_db_conn():
    return await asyncpg.connect(os.getenv("DATABASE_URL"))

@app.get("/api/jobs")
async def get_all_jobs():
    conn = await get_db_conn()
    try:
        rows = await conn.fetch("SELECT * FROM job_queue ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in rows]
    finally:
        await conn.close()

@app.get("/api/job/{job_id}")
async def get_job(job_id: int):
    conn = await get_db_conn()
    try:
        row = await conn.fetchrow("SELECT * FROM job_queue WHERE job_id = $1", job_id)
        return dict(row) if row else {"error": "Not found"}
    finally:
        await conn.close()
