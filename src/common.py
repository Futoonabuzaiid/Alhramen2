"""Shared helpers: rate-limited/resumable HTTP fetch with on-disk caching, logging."""
import json
import logging
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MIN_INTERVAL = 0.4  # ~2.5 req/s max
MAX_RETRIES = 5

_last_request_ts = [0.0]


def get_logger(name: str, logs_dir: str = None) -> logging.Logger:
    logs_path = Path(logs_dir) if logs_dir else (PROJECT_ROOT / "logs")
    logs_path.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logs_path / f"{name}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def _throttle():
    elapsed = time.monotonic() - _last_request_ts[0]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_request_ts[0] = time.monotonic()


def fetch_json_cached(url: str, cache_path: Path, logger: logging.Logger, session: requests.Session = None):
    """Fetch JSON from url, caching raw bytes at cache_path. Resumable: skips if cache exists."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        logger.info(f"cache hit: {cache_path}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    backoff = 1.0
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                cache_path.write_text(resp.text, encoding="utf-8")
                logger.info(f"fetched: {url} -> {cache_path}")
                return json.loads(resp.text)
            elif resp.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"retryable HTTP {resp.status_code} for {url}, attempt {attempt}/{MAX_RETRIES}")
                last_exc = RuntimeError(f"HTTP {resp.status_code}")
            else:
                logger.error(f"HTTP {resp.status_code} for {url}, not retrying")
                return None
        except requests.RequestException as e:
            logger.warning(f"request error for {url}: {e}, attempt {attempt}/{MAX_RETRIES}")
            last_exc = e
        time.sleep(backoff)
        backoff = min(backoff * 2, 30)
    logger.error(f"giving up on {url}: {last_exc}")
    return None


def fetch_binary_cached(url: str, cache_path: Path, logger: logging.Logger, session: requests.Session = None) -> bool:
    """Fetch binary content (e.g. a .zip) from url, caching raw bytes at cache_path.
    Resumable: skips the request entirely if cache_path already exists.
    Returns True if cache_path exists and is populated after the call."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        logger.info(f"cache hit: {cache_path}")
        return True

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    backoff = 1.0
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            resp = session.get(url, timeout=60)
            if resp.status_code == 200:
                cache_path.write_bytes(resp.content)
                logger.info(f"fetched: {url} -> {cache_path} ({len(resp.content)} bytes)")
                return True
            elif resp.status_code in (429, 500, 502, 503, 504):
                logger.warning(f"retryable HTTP {resp.status_code} for {url}, attempt {attempt}/{MAX_RETRIES}")
                last_exc = RuntimeError(f"HTTP {resp.status_code}")
            else:
                logger.error(f"HTTP {resp.status_code} for {url}, not retrying")
                return False
        except requests.RequestException as e:
            logger.warning(f"request error for {url}: {e}, attempt {attempt}/{MAX_RETRIES}")
            last_exc = e
        time.sleep(backoff)
        backoff = min(backoff * 2, 30)
    logger.error(f"giving up on {url}: {last_exc}")
    return False
