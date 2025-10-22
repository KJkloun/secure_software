from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

WINDOW_SECONDS = 60
ENV_RATE_LIMIT = "IDEA_RATE_LIMIT_PER_MINUTE"
DEFAULT_RATE_LIMIT = 100

MAX_ATTACHMENT_BYTES = 5_000_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"


class AttachmentValidationError(Exception):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class RateLimiter:
    def __init__(self, window_seconds: int = WINDOW_SECONDS) -> None:
        self.window_seconds = window_seconds
        self._hits: Dict[str, List[float]] = {}

    def reset(self) -> None:
        self._hits.clear()

    def resolve_limit(self) -> int:
        raw = os.getenv(ENV_RATE_LIMIT)
        if raw is None or raw.strip() == "":
            return DEFAULT_RATE_LIMIT
        try:
            parsed = int(raw)
        except ValueError:
            return DEFAULT_RATE_LIMIT
        return max(1, parsed)

    def allow(self, key: str, limit: int | None = None) -> bool:
        now = time.monotonic()
        bucket = self._hits.setdefault(key, [])
        threshold = now - self.window_seconds
        bucket = [stamp for stamp in bucket if stamp > threshold]
        if limit is None:
            limit = self.resolve_limit()
        if len(bucket) >= limit:
            self._hits[key] = bucket
            return False
        bucket.append(now)
        self._hits[key] = bucket
        return True


@dataclass
class AttachmentResult:
    filename: str
    content_type: str
    path: Path


class AttachmentStorage:
    def __init__(self, base_dir: Path | str) -> None:
        self._base_dir = self._prepare_dir(base_dir)

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def configure(self, base_dir: Path | str) -> None:
        self._base_dir = self._prepare_dir(base_dir)

    def _prepare_dir(self, base_dir: Path | str) -> Path:
        path = Path(base_dir).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save(self, data: bytes) -> AttachmentResult:
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise AttachmentValidationError(
                code="attachment_too_large",
                detail="attachment exceeds size limit",
            )
        content_type = self._sniff_content_type(data)
        if content_type is None:
            raise AttachmentValidationError(
                code="attachment_bad_type",
                detail="unsupported attachment type",
            )
        filename = self._generate_name(content_type)
        path = (self._base_dir / filename).resolve()
        if not str(path).startswith(str(self._base_dir)):
            raise AttachmentValidationError(
                code="attachment_path_violation",
                detail="resolved path escapes storage root",
            )
        if any(segment.is_symlink() for segment in path.parents):
            raise AttachmentValidationError(
                code="attachment_symlink_detected",
                detail="symlink detected in storage path",
            )
        with path.open("wb") as handle:
            handle.write(data)
        return AttachmentResult(filename=filename, content_type=content_type, path=path)

    def _generate_name(self, content_type: str) -> str:
        suffix = ".png" if content_type == "image/png" else ".jpg"
        return f"{uuid.uuid4()}{suffix}"

    def _sniff_content_type(self, data: bytes) -> str | None:
        if data.startswith(PNG_SIGNATURE):
            return "image/png"
        if data.startswith(JPEG_SOI) and data.endswith(JPEG_EOI):
            return "image/jpeg"
        return None
