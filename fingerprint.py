"""
fingerprint.py — Track A visual pHash fingerprinting for SeekReap Tier-3
Fetches YouTube thumbnail → computes pHash → compares against DB → stores result.
"""
import os, urllib.request, io, hashlib, logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_yX7aHMwIqQC4@ep-rapid-base-ai27r1sa-pooler.c-4.us-east-1.aws.neon.tech:5432/seekreap_neon_db?sslmode=require"
)

# pHash Hamming distance threshold for a "match"
# 64-bit pHash: 0=identical, <=10=near-duplicate, <=20=similar
MATCH_THRESHOLD   = 20   # similar
DUPE_THRESHOLD    = 6    # near-identical

def _get_thumbnail_url(video_url: str) -> Optional[str]:
    """Extract YouTube video ID and return maxresdefault thumbnail URL."""
    import re
    patterns = [
        r"(?:v=|youtu\.be/|/v/|/embed/|/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, video_url)
        if m:
            vid = m.group(1)
            return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
    return None

def _compute_phash(image_bytes: bytes) -> Optional[str]:
    """Compute perceptual hash of image bytes. Returns 16-char hex string."""
    try:
        import imagehash
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        h   = imagehash.phash(img, hash_size=8)   # 64-bit hash
        return str(h)
    except Exception as e:
        logger.warning("pHash computation failed: %s", e)
        return None

def _hamming(h1: str, h2: str) -> int:
    """Hamming distance between two hex pHash strings."""
    try:
        a = int(h1, 16)
        b = int(h2, 16)
        return bin(a ^ b).count("1")
    except Exception:
        return 64   # max distance on error

def _phash_to_similarity(min_distance: int) -> float:
    """Convert minimum Hamming distance to 0-100 similarity score."""
    # 0 distance → 100% similar, 32+ distance → 0% similar
    return round(max(0.0, (32 - min_distance) / 32 * 100), 1)

def run_fingerprint(
    submission_id: str,
    creator_id: str,
    content_url: str,
) -> dict:
    """
    Main entry point called from Tier-3 analysis pipeline.
    Returns dict with visual_similarity_score, closest_match, thumbnail_url, phash.
    """
    result = {
        "visual_similarity_score": 0.0,
        "closest_match_id":        None,
        "closest_match_url":       None,
        "closest_match_distance":  64,
        "thumbnail_url":           None,
        "visual_phash":            None,
        "fingerprint_stored":      False,
        "error":                   None,
    }

    # 1. Get thumbnail URL
    thumb_url = _get_thumbnail_url(content_url)
    if not thumb_url:
        result["error"] = "Could not extract video ID from URL"
        return result
    result["thumbnail_url"] = thumb_url

    # 2. Download thumbnail
    try:
        req = urllib.request.Request(thumb_url, headers={"User-Agent": "SeekReap/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            image_bytes = resp.read()
    except Exception as e:
        result["error"] = f"Thumbnail download failed: {e}"
        return result

    # 3. Compute pHash
    phash = _compute_phash(image_bytes)
    if not phash:
        result["error"] = "pHash computation failed"
        return result
    result["visual_phash"] = phash

    # 4. Compare against existing fingerprints in DB
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur  = conn.cursor()

        cur.execute(
            "SELECT id, content_url, visual_phash FROM fingerprints "
            "WHERE visual_phash IS NOT NULL AND submission_id != %s",
            (submission_id,)
        )
        rows = cur.fetchall()

        min_dist  = 64
        best_row  = None
        for row in rows:
            d = _hamming(phash, row[2])
            if d < min_dist:
                min_dist = d
                best_row = row

        if best_row and min_dist <= MATCH_THRESHOLD:
            result["closest_match_id"]       = str(best_row[0])
            result["closest_match_url"]      = best_row[1]
            result["closest_match_distance"] = min_dist
            result["visual_similarity_score"] = _phash_to_similarity(min_dist)
        else:
            result["visual_similarity_score"] = _phash_to_similarity(min_dist)

        # 5. Store this fingerprint
        cur.execute(
            """
            INSERT INTO fingerprints
                (submission_id, creator_id, content_url, visual_phash, thumbnail_url, fingerprint_version)
            VALUES (%s, %s, %s, %s, %s, 'phash-v1')
            ON CONFLICT DO NOTHING
            """,
            (submission_id, creator_id, content_url, phash, thumb_url)
        )
        conn.commit()
        cur.close()
        conn.close()
        result["fingerprint_stored"] = True

    except Exception as e:
        logger.error("DB fingerprint operation failed: %s", e)
        result["error"] = f"DB error: {e}"

    return result
