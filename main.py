from fastapi import FastAPI, Request
from typing import Dict
from pydantic import BaseModel
import subprocess
import tempfile
import os
import json as _json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Binary check at startup
import shutil
print("ffmpeg:", shutil.which("ffmpeg"))
print("fpcalc:", shutil.which("fpcalc"))

app = FastAPI()

FLAG_WEIGHTS = {
    "high_confidence_duplicate": 0.50,
    "probable_duplicate":        0.25,
    "duplicate_content":         0.10,
    "audio_match":               0.05,
    "visual_match":              0.10,
}

def compute_risk_score(audio_similarity: float = 0.0,
                       visual_similarity: float = 0.0,
                       flags: list = None) -> tuple[float, str]:
    flags = flags or []
    flag_score = min(sum(FLAG_WEIGHTS.get(f, 0.02) for f in flags), 0.5)
    risk_score = (
        audio_similarity * 0.5 +
        visual_similarity * 0.3 +
        flag_score * 0.2
    )
    risk_score = max(0.0, min(risk_score, 1.0))
    if "high_confidence_duplicate" in flags:
        risk_level = "high"
    elif risk_score >= 0.75:
        risk_level = "high"
    elif risk_score >= 0.4:
        risk_level = "medium"
    else:
        risk_level = "low"
    return risk_score, risk_level

class AnalyzeRequest(BaseModel):
    content_id: str
    content_type: str
    content_data: Dict

@app.post("/api/analyze")
async def analyze_content(req: AnalyzeRequest) -> Dict:
    result = {
        "content_id": req.content_id,
        "content_type": req.content_type,
        "signals": req.content_data,
    }
    score, level = compute_risk_score(
        audio_similarity=req.content_data.get("audio_similarity", 0.0),
        visual_similarity=req.content_data.get("visual_similarity", 0.0),
        flags=req.content_data.get("flags", [])
    )
    result["risk_score"] = score
    result["risk_level"] = level
    return result

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ── Internal: audio fingerprint from uploaded file ──
@app.post("/internal/audio-fingerprint")
async def get_audio_fingerprint(request: Request):
    """Accept uploaded file and return fingerprint."""
    form = await request.form()
    file = form.get("file")
    if not file:
        return {"error": "file required"}
    
    try:
        # Save uploaded file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            content = await file.read()
            tmp.write(content)
            input_path = tmp.name
            logger.info(f"Saved temp file: {input_path} ({len(content)} bytes)")
        
        # Convert to audio and fingerprint
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "audio.mp4")
            logger.info(f"Converting to {out_path}")
            
            # ffmpeg conversion
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", input_path,
                 "-t", "120", "-vn", "-acodec", "aac", "-b:a", "128k", "-f", "mp4", out_path],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0:
                logger.error(f"ffmpeg failed: {result.stderr}")
                return {"error": f"ffmpeg failed: {result.stderr}"}
            
            logger.info("ffmpeg conversion successful")
            
            # fpcalc fingerprint
            fp_result = subprocess.run(
                ["fpcalc", "-json", out_path],
                capture_output=True, text=True, timeout=30
            )
            if fp_result.returncode != 0:
                logger.error(f"fpcalc failed: {fp_result.stderr}")
                return {"error": f"fpcalc failed: {fp_result.stderr}"}
            
            if not fp_result.stdout:
                logger.error("fpcalc returned empty output")
                return {"error": "fpcalc returned empty output"}
            
            logger.info(f"fpcalc output: {fp_result.stdout[:200]}")
            try:
                data = _json.loads(fp_result.stdout)
            except Exception as e:
                logger.error(f"Invalid fpcalc JSON: {e}")
                return {
                    "error": "invalid fpcalc JSON",
                    "raw_output": fp_result.stdout[:500]
                }
            
            # Clean up
            os.unlink(input_path)
            
            return {
                "fingerprint": data["fingerprint"],
                "duration": float(data["duration"])
            }
            
    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout: {e}")
        return {"error": f"Timeout: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": str(e)}

# ── Internal: visual pHash fingerprint from thumbnail ──
@app.post("/internal/visual-fingerprint")
async def get_visual_fingerprint(request: Request):
    import httpx as _httpx
    import imagehash
    from PIL import Image
    import io
    body = await request.json()
    thumbnail_url = body.get("thumbnail_url", "")
    if not thumbnail_url:
        return {"error": "thumbnail_url required"}
    try:
        async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(thumbnail_url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            phash = str(imagehash.phash(img))
            return {"phash": phash, "thumbnail_url": thumbnail_url}
    except Exception as e:
        return {"error": str(e)}
