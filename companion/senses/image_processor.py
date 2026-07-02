"""
companion/senses/image_processor.py
======================================
Processes raw screenshots for efficient cloud VLM transmission.
Steps: resize → compress to JPEG 60% → MD5 dedup filter.
Minimizes bandwidth and API token usage.
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False
    logger.warning("Pillow not installed — image processing limited")


class ImageProcessor:
    """
    Processes screenshots for VLM API submission.

    Pipeline:
    1. Decode PNG from mss
    2. Resize to max dimensions (default 1280x720)
    3. Compress to JPEG at 60% quality
    4. Compute MD5 for deduplication
    5. Return processed bytes only if content changed
    """

    def __init__(
        self,
        max_width: int = 1280,
        max_height: int = 720,
        jpeg_quality: int = 60,
    ) -> None:
        self.max_width = max_width
        self.max_height = max_height
        self.jpeg_quality = jpeg_quality
        self._last_hash: Optional[str] = None
        self._processed_count: int = 0
        self._duplicate_count: int = 0

    def process(self, png_bytes: bytes) -> Optional[bytes]:
        """
        Process a raw PNG screenshot.

        Args:
            png_bytes: Raw PNG image bytes from screen capture.

        Returns:
            JPEG bytes if content changed since last call,
            None if duplicate (no significant change).
        """
        if not _PIL_AVAILABLE:
            # Fallback: return raw bytes with MD5 check only
            return self._hash_check_only(png_bytes)

        try:
            # Open image
            img = Image.open(io.BytesIO(png_bytes))

            # Convert to RGB (remove alpha channel if present)
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize maintaining aspect ratio
            if img.width > self.max_width or img.height > self.max_height:
                img.thumbnail((self.max_width, self.max_height), Image.LANCZOS)

            # Compress to JPEG
            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format="JPEG", quality=self.jpeg_quality, optimize=True)
            jpeg_bytes = jpeg_buffer.getvalue()

            # MD5 deduplication
            md5 = hashlib.md5(jpeg_bytes).hexdigest()
            if md5 == self._last_hash:
                self._duplicate_count += 1
                logger.debug(f"Duplicate frame skipped (MD5: {md5[:8]}…)")
                return None

            self._last_hash = md5
            self._processed_count += 1
            logger.debug(
                f"Frame processed: {img.width}x{img.height} → "
                f"{len(jpeg_bytes)//1024}KB JPEG"
            )
            return jpeg_bytes

        except Exception as exc:
            logger.error(f"Image processing failed: {exc}", exc_info=True)
            return None

    def _hash_check_only(self, data: bytes) -> Optional[bytes]:
        """Fallback when PIL unavailable — only does MD5 check."""
        md5 = hashlib.md5(data[:4096]).hexdigest()  # Hash first 4KB for speed
        if md5 == self._last_hash:
            self._duplicate_count += 1
            return None
        self._last_hash = md5
        return data

    def force_next_send(self) -> None:
        """Force the next frame to be sent regardless of MD5 match."""
        self._last_hash = None

    def stats(self) -> dict:
        total = self._processed_count + self._duplicate_count
        return {
            "processed_frames": self._processed_count,
            "duplicate_frames_skipped": self._duplicate_count,
            "dedup_rate_percent": round(
                (self._duplicate_count / total * 100) if total > 0 else 0.0, 1
            ),
        }
