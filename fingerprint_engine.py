"""
Perceptual Fingerprinting Engine for SeekReap
"""

import hashlib
import numpy as np
from typing import Dict, Any, List
import json

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
    return {
        "type": "video",
        "algorithm": "placeholder",
        "fingerprint_hash": hashlib.sha256(f"video:{video_path}".encode()).hexdigest()[:32]
    }


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
