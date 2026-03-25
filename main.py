from fastapi import FastAPI, Request
from typing import Dict
from pydantic import BaseModel

app = FastAPI()

# Flag weights — higher weight = more contribution to risk score
FLAG_WEIGHTS = {
    "high_confidence_duplicate": 0.50,  # near-identical copy — very high signal
    "probable_duplicate":        0.25,  # strong similarity — significant signal
    "duplicate_content":         0.10,  # generic duplicate marker
    "audio_match":               0.05,  # similarity above threshold
    "visual_match":              0.10,  # visual pHash similarity above threshold
}

def compute_risk_score(audio_similarity: float = 0.0,
                       visual_similarity: float = 0.0,
                       flags: list = None) -> tuple[float, str]:
    flags = flags or []
    # Weighted flag score — capped at 0.5 to prevent flags alone maxing out score
    flag_score = min(sum(FLAG_WEIGHTS.get(f, 0.02) for f in flags), 0.5)
    risk_score = (
        audio_similarity * 0.5 +
        visual_similarity * 0.3 +
        flag_score * 0.2
    )
    risk_score = max(0.0, min(risk_score, 1.0))
    # Explicit override: high_confidence_duplicate always forces high risk
    # regardless of formula output — a bit-perfect match is never "medium"
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


# ── Internal: visual pHash fingerprint from thumbnail URL ──
@app.post("/internal/visual-fingerprint")
async def get_visual_fingerprint(request: Request):
    """
    Called by Tier-5. Downloads thumbnail and computes perceptual hash.
    Returns: {"phash": "abc123...", "thumbnail_url": "..."} or {"error": "..."}
    """
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

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── Internal: stream URL proxy (legacy, kept for compatibility) ──
@app.post("/internal/stream-url")
async def get_stream_url(request: Request):
    import subprocess
    body = await request.json()
    content_url = body.get("content_url", "")
    if not content_url:
        return {"error": "content_url required"}
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "--format", "worstaudio/bestaudio", "--cookies", "cookies.txt",
             "--get-url", "--no-warnings", "--socket-timeout", "15",
             "--extractor-retries", "1", content_url],
            capture_output=True, text=True, timeout=25
        )
        if result.returncode != 0:
            return {"error": f"yt-dlp failed: {result.stderr.strip()[:300]}"}
        stream_url = result.stdout.strip().splitlines()[0]
        if not stream_url:
            return {"error": "yt-dlp returned empty URL"}
        return {"stream_url": stream_url}
    except subprocess.TimeoutExpired:
        return {"error": "yt-dlp timed out after 25s"}
    except Exception as e:
        return {"error": str(e)}


# ── Internal: full audio fingerprint pipeline for Tier-5 ──
@app.post("/internal/audio-fingerprint")
async def get_audio_fingerprint(request: Request):
    """
    Called by Tier-5. Runs full pipeline on Tier-3 (unrestricted egress):
      yt-dlp --get-url → ffmpeg -t 120 → fpcalc
    Returns: {"fingerprint": "...", "duration": 123.4} or {"error": "..."}
    """
    import subprocess, tempfile, os, json as _json
    body = await request.json()
    content_url = body.get("content_url", "")
    if not content_url:
        return {"error": "content_url required"}
    try:
        # Step 1: get stream URL via yt-dlp
        r = subprocess.run(
            ["yt-dlp", "--no-playlist", "--format", "worstaudio/bestaudio", "--cookies", "cookies.txt",
             "--get-url", "--no-warnings", "--socket-timeout", "15",
             "--extractor-retries", "1", content_url],
            capture_output=True, text=True, timeout=25
        )
        if r.returncode != 0:
            return {"error": f"yt-dlp failed: {r.stderr.strip()[:300]}"}
        stream_url = r.stdout.strip().splitlines()[0]
        if not stream_url:
            return {"error": "yt-dlp returned empty URL"}

        # Step 2: download first 120s via ffmpeg
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "audio.m4a")
            subprocess.run(
                ["ffmpeg", "-y", "-t", "120", "-i", stream_url,
                 "-vn", "-acodec", "copy", "-loglevel", "error", out_path],
                check=True, timeout=180
            )
            # Step 3: chromaprint fingerprint
            fp = subprocess.run(
                ["fpcalc", "-json", out_path],
                capture_output=True, text=True, timeout=30, check=True
            )
            data = _json.loads(fp.stdout)
            return {"fingerprint": data["fingerprint"], "duration": float(data["duration"])}

    except subprocess.TimeoutExpired as e:
        return {"error": f"timed out: {e}"}
    except Exception as e:
        return {"error": str(e)}

# ── Internal: audio fingerprint from uploaded file ──
@app.post("/internal/audio-fingerprint-file")
async def get_audio_fingerprint_file(request: Request):
    """
    Called by Tier-5. Accepts uploaded audio/video file and returns fingerprint.
    """
    import subprocess, tempfile, os, json as _json
    import aiofiles
    
    form = await request.form()
    file = form.get("file")
    if not file:
        return {"error": "file required"}
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            content = await file.read()
            tmp.write(content)
            input_path = tmp.name
        
        # Convert to audio and fingerprint
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "audio.mp4")
            
            # Convert to audio with ffmpeg
            subprocess.run(
                ["ffmpeg", "-y", "-i", input_path,
                 "-t", "120", "-vn", "-acodec", "aac", "-b:a", "128k", "-f", "mp4", out_path],
                check=True, capture_output=True, timeout=180
            )
            
            # Generate fingerprint
            fp = subprocess.run(
                ["fpcalc", "-json", out_path],
                capture_output=True, text=True, timeout=30, check=True
            )
            data = _json.loads(fp.stdout)
            
            # Clean up
            os.unlink(input_path)
            
            return {
                "fingerprint": data["fingerprint"],
                "duration": float(data["duration"])
            }
            
    except subprocess.CalledProcessError as e:
        return {"error": f"ffmpeg/fpcalc failed: {e.stderr.decode() if e.stderr else str(e)}"}
    except Exception as e:
        return {"error": str(e)}
