"""
Perceptual Fingerprinting Engine for SeekReap
Supports: images, audio, text, code
"""

import hashlib
import numpy as np
from typing import Dict, Any, List, Tuple
import json

# Image fingerprinting
try:
    from PIL import Image
    import imagehash
    IMAGE_HASH_AVAILABLE = True
except ImportError:
    IMAGE_HASH_AVAILABLE = False

# Audio fingerprinting
try:
    import librosa
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# Text similarity
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    TEXT_AVAILABLE = True
except ImportError:
    TEXT_AVAILABLE = False


def fingerprint_image(image_path: str) -> Dict[str, Any]:
    """Generate perceptual hash for images using pHash"""
    if not IMAGE_HASH_AVAILABLE:
        return {"error": "imagehash not available", "fingerprint": None}
    
    try:
        img = Image.open(image_path)
        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))
        ahash = str(imagehash.average_hash(img))
        
        return {
            "type": "image",
            "algorithm": "phash",
            "perceptual_hash": phash,
            "difference_hash": dhash,
            "average_hash": ahash,
            "hash_size": 64
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_audio(audio_path: str) -> Dict[str, Any]:
    """Generate acoustic fingerprint for audio"""
    if not AUDIO_AVAILABLE:
        return {"error": "librosa not available", "fingerprint": None}
    
    try:
        y, sr = librosa.load(audio_path, duration=30)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1).tolist()
        
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1).tolist()
        
        feature_string = f"{chroma_mean[:10]}{mfcc_mean[:10]}"
        fingerprint_hash = hashlib.sha256(feature_string.encode()).hexdigest()[:32]
        
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
    """Generate text fingerprint"""
    try:
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:32]
        
        return {
            "type": "text",
            "algorithm": "hash",
            "fingerprint_hash": text_hash,
            "text_preview": text[:500] if len(text) > 500 else text,
            "length": len(text)
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def fingerprint_video(video_path: str) -> Dict[str, Any]:
    """Generate composite fingerprint for video"""
    return {
        "type": "video",
        "algorithm": "placeholder",
        "fingerprint_hash": hashlib.sha256(f"video:{video_path}".encode()).hexdigest()[:32]
    }


def fingerprint_code(code: str, language: str = "python") -> Dict[str, Any]:
    """Generate structural fingerprint for code"""
    try:
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:32]
        return {
            "type": "code",
            "language": language,
            "algorithm": "hash",
            "fingerprint_hash": code_hash
        }
    except Exception as e:
        return {"error": str(e), "fingerprint": None}


def generate_fingerprint(content_type: str, content_path: str = None, content_text: str = None) -> Dict[str, Any]:
    """Main entry point for fingerprint generation"""
    fingerprinters = {
        "image": lambda: fingerprint_image(content_path) if content_path else fingerprint_text(content_text or ""),
        "audio": lambda: fingerprint_audio(content_path) if content_path else {"error": "no file path"},
        "video": lambda: fingerprint_video(content_path) if content_path else {"error": "no file path"},
        "text": lambda: fingerprint_text(content_text or ""),
        "code": lambda: fingerprint_code(content_text or "", "python"),
        "pdf": lambda: fingerprint_text(content_text or ""),
        "epub": lambda: fingerprint_text(content_text or "")
    }
    
    fingerprinter = fingerprinters.get(content_type, fingerprinters["text"])
    return fingerprinter()


def compare_fingerprints(fp1: Dict[str, Any], fp2: Dict[str, Any]) -> float:
    """Compare two fingerprints and return similarity score (0-1)"""
    if not fp1 or not fp2:
        return 0.0
    
    if fp1.get("type") != fp2.get("type"):
        return 0.0
    
    fp_type = fp1.get("type")
    
    if fp_type == "image" and IMAGE_HASH_AVAILABLE:
        try:
            hash1 = imagehash.hex_to_hash(fp1.get("perceptual_hash", ""))
            hash2 = imagehash.hex_to_hash(fp2.get("perceptual_hash", ""))
            max_diff = len(hash1.hash) ** 2
            similarity = 1 - (hash1 - hash2) / max_diff
            return max(0.0, min(1.0, similarity))
        except:
            return 0.0
    
    elif fp_type == "audio":
        try:
            chroma1 = np.array(fp1.get("chroma_features", []))
            chroma2 = np.array(fp2.get("chroma_features", []))
            if len(chroma1) > 0 and len(chroma2) > 0:
                norm1 = np.linalg.norm(chroma1)
                norm2 = np.linalg.norm(chroma2)
                if norm1 > 0 and norm2 > 0:
                    similarity = np.dot(chroma1, chroma2) / (norm1 * norm2)
                    return max(0.0, min(1.0, similarity))
        except:
            pass
        return 0.0
    
    else:
        # Exact match for text/code
        if fp1.get("fingerprint_hash") == fp2.get("fingerprint_hash"):
            return 1.0
        return 0.0


def find_similar_submissions(cursor, fingerprint: Dict[str, Any], threshold: float = 0.85) -> List[Dict]:
    """Find existing submissions similar to the given fingerprint"""
    # This is a simplified version - would need actual DB query
    # For now, return empty list
    return []
