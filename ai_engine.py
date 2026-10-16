"""Runtime-only shared helpers for RoboMANTAP HTMX service.

This file intentionally excludes Streamlit/admin/report generators from the main
RoboMANTAP ai_engine.py. Public helper names used by this service are preserved.
"""
import json
import os
import re
import time
from datetime import datetime, timezone, timedelta

from google import genai
from google.genai import types
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def _load_gemini_api_keys():
    """Read one key or a JSON/comma-separated list without logging secret values."""
    raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
    if isinstance(raw, (list, tuple)):
        values = list(raw)
    else:
        raw = str(raw).strip()
        values = []
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    values = parsed
            except (ValueError, TypeError):
                # Tolerate multiline values with backslash line continuations.
                cleaned = raw.replace("\\\r\n", "").replace("\\\n", "")
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        values = parsed
                except (ValueError, TypeError):
                    values = []
        if not values:
            values = raw.split(",")
    result = []
    for value in values:
        key = str(value).strip().strip("\"' ")
        if key and key not in result:
            result.append(key)
    return result

api_keys = _load_gemini_api_keys()
print(f"[HTMX] Gemini configuration: {len(api_keys)} key(s) detected")
QUIZ_MODELS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
STREAM_MODELS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
STREAM_HINT_MAX_TOKENS = 9000
STREAM_SOLUTION_MAX_TOKENS = 9000
STREAM_TIMEOUT_MS = 90_000
_clients_cache = None
_db_conn_cache = None

def get_gemini_clients():
    """
    Reuse koneksi Gemini antar request.
    Menggunakan caching global yang kompatibel untuk Streamlit maupun Uvicorn FastAPI.
    """
    global _clients_cache
    if _clients_cache is not None:
        return _clients_cache

    clients = []
    for key in api_keys:
        try:
            clients.append(
                genai.Client(
                    api_key=key,
                    http_options=types.HttpOptions(
                        timeout=STREAM_TIMEOUT_MS,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
            )
        except Exception:
            continue

    _clients_cache = clients
    return clients

def _stream_config(model_name: str, max_output_tokens: int):
    if model_name.startswith("gemini-3."):
        return types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_level="high"
            ),
        )

    return types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        thinking_config=types.ThinkingConfig(
            thinking_budget=0,
            include_thoughts=False,
        ),
    )

def _buffer_stream_text(source, min_chars: int = 2, flush_seconds: float = 0.01):
    buffer = []
    size = 0
    last_flush = time.monotonic()

    for chunk in source:
        if not chunk:
            continue

        buffer.append(chunk)
        size += len(chunk)

        now = time.monotonic()
        if size >= min_chars or (now - last_flush) >= flush_seconds:
            yield "".join(buffer)
            buffer.clear()
            size = 0
            last_flush = now

    if buffer:
        yield "".join(buffer)

def _stream_from_clients(prompt: str, max_output_tokens: int):
    clients = get_gemini_clients()

    if not clients:
        yield "⚠️ Tidak ada koneksi yang aktif nih. Coba Kamu klik lagi.."
        return

    for client in clients:
        for model_name in STREAM_MODELS:
            try:
                response = client.models.generate_content_stream(
                    model=model_name,
                    contents=prompt,
                    config=_stream_config(model_name, max_output_tokens),
                )

                emitted = False

                def raw_stream():
                    for chunk in response:
                        chunk_text = getattr(chunk, "text", None)
                        if chunk_text:
                            yield chunk_text

                for piece in _buffer_stream_text(raw_stream()):
                    emitted = True
                    yield piece

                if emitted:
                    return

            except Exception:
                continue

    yield (
        "⚠️ Maaf ya, koneksi sedang bermasalah atau kuota sedang penuh nih. "
        "Silakan coba klik lagi ya!"
    )

# Label opsi jawaban yang dipakai bersama oleh Kuis dan TKA.
# MTs menggunakan empat opsi (A-D), sedangkan MA menggunakan lima opsi (A-E).
OPTION_LABELS_MTS = ("A", "B", "C", "D")
OPTION_LABELS_MA = ("A", "B", "C", "D", "E")


def option_labels_for_jenjang(jenjang: str) -> tuple[str, ...]:
    """MTs -> A-D, MA -> A-E. Default aman mengikuti MTs untuk jenjang tidak dikenal."""
    value = str(jenjang or "").strip().lower()
    if "ma" in value or "aliyah" in value:
        return OPTION_LABELS_MA
    return OPTION_LABELS_MTS

def option_count_for_jenjang(jenjang: str) -> int:
    return len(option_labels_for_jenjang(jenjang))

def _split_option_label(value: str, fallback_index: int = 0):
    text = str(value or "").strip()
    match = re.match(r"^\s*([A-Ea-e])\s*[\.\)\:\-]\s*(.*)$", text, flags=re.DOTALL)
    if match:
        return match.group(1).upper(), match.group(2).strip()
    fallback = chr(65 + fallback_index)
    return fallback, text

def normalize_quiz_options(options, jenjang: str):
    """Normalisasi label opsi ke A. ... / B. ... tanpa mengubah isi pilihan."""
    expected = option_labels_for_jenjang(jenjang)
    normalized = []
    for idx, raw in enumerate(options or []):
        label, body = _split_option_label(raw, idx)
        normalized.append(f"{label}. {body}" if body else f"{label}.")
    return normalized, expected

def clean_json_text(text: str) -> str:
    if not text:
        return ""
    
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    def replace_slash(match):
        g = match.group(0)
        if g in (r'\\', r'\"'):
            return g 
        return r'\\' 

    return re.sub(r'\\\\|\\"|\\', replace_slash, text)

def stream_ai_text(prompt: str, max_output_tokens: int = STREAM_HINT_MAX_TOKENS):
    yield from _stream_from_clients(
        prompt,
        max_output_tokens=max_output_tokens,
    )

def get_ai_hint_stream(question: str, user_attempt: str, mapel: str = "Umum"):
    prompt = f"""
    Kamu adalah 'RoboMANTAP', teman belajar dan asisten AI yang ramah, santai, ceria, dan sangat suportif dari MTs & MA Al Irsyad Putri Bondowoso (MANTAP).
    Gunakan gaya bahasa memberi sapaan 'aku' dan 'kamu' yang bersahabat namun tetap edukatif.

    Mata Pelajaran: {mapel}
    Soal OMI: {question}
    Ide Pengerjaan Siswa: {user_attempt}

    Instruksi:
    - Jangan berikan salam pembuka yang berlebihan.
    - Berikan petunjuk atau bimbingan logika interaktif yang menyemangati dan memuji usaha siswa.
    - Bantu siswa menemukan celah penyelesaian soal bidang {mapel} ini secara natural, runtut, dan analitis step-by-step tanpa membocorkan jawaban akhir.
    - Gunakan format LaTeX $...$ HANYA jika terdapat notasi matematika/sains.
    """
    return stream_ai_text(prompt, max_output_tokens=STREAM_HINT_MAX_TOKENS)

class DBWrapper:
    """Small SQLAlchemy session wrapper used by the HTMX runtime."""
    def __init__(self, engine):
        self.engine = engine
        self.SessionMaker = sessionmaker(bind=self.engine)

    @property
    def session(self):
        return self.SessionMaker()

def init_db_connection():
    """Create/reuse PostgreSQL connection from Vercel Environment Variables."""
    global _db_conn_cache
    if _db_conn_cache is not None:
        return _db_conn_cache
    db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if not db_url:
        print("[DB CONFIG ERROR] DATABASE_URL/POSTGRES_URL belum diatur.")
        return None
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://") and "+" not in db_url.split(":", 1)[0]:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            pool_recycle=300,
            connect_args={"connect_timeout": 5},
        )
        _db_conn_cache = DBWrapper(engine)
        return _db_conn_cache
    except Exception as exc:
        # Do not print credentials/connection URL to logs.
        print(f"[DB INIT ERROR] {type(exc).__name__}: gagal membuat koneksi PostgreSQL.")
        return None

