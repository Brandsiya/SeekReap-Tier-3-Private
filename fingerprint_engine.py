"""
Perceptual Fingerprinting Engine for SeekReap
"""

import hashlib
import numpy as np
from typing import Dict, Any, List
import json
import os
import tempfile
import requests

try:
    from PIL import Image
    import imagehash
    IMAGE_HASH_AVAILABLE = True
except ImportError:
    IMAGE_HASH_AVAILABLE = False

try:
    import librosa
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    TEXT_AVAILABLE = True
except ImportError:
    TEXT_AVAILABLE = False


def _download_to_temp(url: str, max_bytes: int = 200 * 1024 * 1024) -> str:
    """Download a remote file (e.g. a Supabase Storage signed URL) to a local
    temp file so existing PIL/librosa/cv2-based fingerprinters can read it.
    Raises on failure — caller should catch and fall back gracefully."""
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    suffix = os.path.splitext(url.split("?")[0])[1][:10] or ".bin"
    fd, path = tempfile.mkstemp(suffix=suffix)
    total = 0
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Remote file exceeds {max_bytes} byte limit")
                f.write(chunk)
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


def fingerprint_image(image_path: str) -> Dict[str, Any]:
    if not IMAGE_HASH_AVAILABLE:
        return {"error": "imagehash not available", "fingerprint": None}
    try:
        img = Image.open(image_path)
        return {
            "type": "image",
            "algorithm": "phash",
            "perceptual_hash": str(imagehash.phash(img)),
            "difference_hash": str(imagehash.dhash(img)),
            "average_hash":    str(imagehash.average_hash(img)),
            "hash_size": 64
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_audio(audio_path: str) -> Dict[str, Any]:
    if not AUDIO_AVAILABLE:
        return {"error": "librosa not available", "fingerprint": None}
    try:
        y, sr = librosa.load(audio_path, duration=30)
        chroma      = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1).tolist()
        mfcc        = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean   = np.mean(mfcc, axis=1).tolist()
        feature_string    = f"{chroma_mean[:10]}{mfcc_mean[:10]}"
        fingerprint_hash  = hashlib.sha256(feature_string.encode()).hexdigest()[:32]
        return {
            "type": "audio",
            "algorithm": "chroma_mfcc",
            "fingerprint_hash": fingerprint_hash,
            "chroma_features": chroma_mean,
            "mfcc_features": mfcc_mean,
            "duration": len(y) / sr
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_text(text: str) -> Dict[str, Any]:
    try:
        return {
            "type": "text",
            "algorithm": "hash",
            "fingerprint_hash": hashlib.sha256(text.encode()).hexdigest()[:32],
            "text_preview": text[:500],
            "length": len(text)
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_video(video_path: str) -> Dict[str, Any]:
    # NOTE: this is still not a perceptual/frame-based video fingerprint —
    # building real frame-sampling perceptual hashing for video is a
    # separate, larger effort. This at least hashes the actual downloaded
    # file bytes (exact-match capable) instead of the file path string,
    # which produced a different "fingerprint" every time regardless of
    # the video's actual content.
    try:
        hasher = hashlib.sha256()
        with open(video_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 256), b""):
                hasher.update(chunk)
        return {
            "type": "video",
            "algorithm": "sha256-exact-match",
            "fingerprint_hash": hasher.hexdigest()[:32],
            "note": "Exact-match only — perceptual video fingerprinting not yet implemented",
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_code(code: str, language: str = "python") -> Dict[str, Any]:
    try:
        return {
            "type": "code",
            "language": language,
            "algorithm": "hash",
            "fingerprint_hash": hashlib.sha256(code.encode()).hexdigest()[:32]
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def generate_fingerprint(content_type: str, content_path: str = None, content_text: str = None) -> Dict[str, Any]:
    downloaded_path = None
    try:
        # content_path may now be a real, fetchable URL (e.g. a Supabase
        # Storage signed URL) rather than a local filesystem path — download
        # it first since PIL/librosa/file-hashing below expect a local path.
        if content_path and content_path.startswith(("http://", "https://")):
            try:
                downloaded_path = _download_to_temp(content_path)
                content_path = downloaded_path
            except Exception as e:
                if content_type in ("audio", "video"):
                    return {"error": f"could not download content: {e}", "fingerprint": None}
                # For text-like types, fall back to title/text fingerprinting
                # rather than failing outright.
                content_path = None

        fingerprinters = {
            "image": lambda: fingerprint_image(content_path) if content_path else fingerprint_text(content_text or ""),
            "audio": lambda: fingerprint_audio(content_path) if content_path else {"error": "no file path"},
            "video": lambda: fingerprint_video(content_path) if content_path else {"error": "no file path"},
            "text":  lambda: fingerprint_text(content_text or ""),
            "code":  lambda: fingerprint_code(content_text or "", "python"),
            "pdf":   lambda: fingerprint_text(content_text or ""),
            "epub":  lambda: fingerprint_text(content_text or "")
        }
        return fingerprinters.get(content_type, fingerprinters["text"])()
    finally:
        if downloaded_path:
            try:
                os.unlink(downloaded_path)
            except OSError:
                pass


def compare_fingerprints(fp1: Dict[str, Any], fp2: Dict[str, Any]) -> float:
    if not fp1 or not fp2:
        return 0.0
    if fp1.get("type") != fp2.get("type"):
        return 0.0

    fp_type = fp1.get("type")

    if fp_type == "image" and IMAGE_HASH_AVAILABLE:
        try:
            h1 = imagehash.hex_to_hash(fp1.get("perceptual_hash", ""))
            h2 = imagehash.hex_to_hash(fp2.get("perceptual_hash", ""))
            max_diff = len(h1.hash) ** 2
            return max(0.0, min(1.0, 1 - (h1 - h2) / max_diff))
        except:
            return 0.0

    elif fp_type == "audio":
        try:
            c1 = np.array(fp1.get("chroma_features", []))
            c2 = np.array(fp2.get("chroma_features", []))
            if len(c1) > 0 and len(c2) > 0:
                n1, n2 = np.linalg.norm(c1), np.linalg.norm(c2)
                if n1 > 0 and n2 > 0:
                    return max(0.0, min(1.0, np.dot(c1, c2) / (n1 * n2)))
        except:
            pass
        return 0.0

    else:
        return 1.0 if fp1.get("fingerprint_hash") == fp2.get("fingerprint_hash") else 0.0


def find_similar_submissions(cursor, fingerprint: Dict[str, Any], threshold: float = 0.85) -> List[Dict]:
    """Query DB fingerprints, compare, return matches above threshold."""
    results = []
    if not fingerprint:
        return results
    try:
        cursor.execute("""
            SELECT
                s.id          AS submission_id,
                s.canonical_id,
                cr.id         AS registry_id,
                f.visual_phash,
                f.id          AS fingerprint_id
            FROM fingerprints f
            JOIN public.submissions s ON s.id = f.submission_id
            LEFT JOIN public.content_registry cr ON cr.submission_id = s.id
            WHERE f.visual_phash IS NOT NULL
        """)
        rows = cursor.fetchall()
        for row in rows:
            stored_fp = {"type": "image", "perceptual_hash": row[3]}
            score = compare_fingerprints(fingerprint, stored_fp)
            if score >= threshold:
                results.append({
                    "submission_id": str(row[0]),
                    "canonical_id":  str(row[1]) if row[1] else None,
                    "registry_id":   str(row[2]) if row[2] else None,
                    "similarity_score": score,
                    "fingerprint_id": str(row[4])
                })
    except Exception as e:
        print(f"Similarity search error: {e}")
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results
