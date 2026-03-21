from fastapi import FastAPI
from typing import Dict
from pydantic import BaseModel

app = FastAPI()

def compute_risk_score(audio_similarity: float = 0.0,
                       visual_similarity: float = 0.0,
                       metadata_flags: int = 0) -> tuple[float, str]:
    meta_score = min(metadata_flags / 5.0, 1.0)
    risk_score = (
        audio_similarity * 0.5 +
        visual_similarity * 0.3 +
        meta_score * 0.2
    )
    risk_score = max(0.0, min(risk_score, 1.0))
    if risk_score >= 0.75:
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
        metadata_flags=len(req.content_data.get("flags", []))
    )

    result["risk_score"] = score
    result["risk_level"] = level
    return result

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
            ["yt-dlp", "--no-playlist", "--format", "worstaudio/bestaudio",
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
            ["yt-dlp", "--no-playlist", "--format", "worstaudio/bestaudio",
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
