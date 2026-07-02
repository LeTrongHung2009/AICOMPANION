"""
companion/senses/mic_capture.py
==================================
Microphone capture using sounddevice.
Captures audio in non-blocking async chunks, detects silence,
and packages into WAV format for Whisper transcription.
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
import time
import wave
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False
    logger.warning("sounddevice not installed — microphone capture disabled")


def _numpy_to_wav(audio_data: np.ndarray, sample_rate: int, channels: int = 1) -> bytes:
    """Convert numpy float32 array to WAV bytes."""
    # Normalize and convert to int16
    if audio_data.dtype != np.int16:
        audio_int16 = (audio_data * 32767).astype(np.int16)
    else:
        audio_int16 = audio_data

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


class MicCapture:
    """
    Asynchronous microphone capture with VAD (Voice Activity Detection).

    Features:
    - Non-blocking async recording
    - RMS-based silence detection
    - Configurable chunk duration
    - Returns WAV bytes ready for Whisper
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 5.0,
        silence_threshold: float = 0.01,
        min_speech_duration: float = 0.5,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.silence_threshold = silence_threshold
        self.min_speech_samples = int(min_speech_duration * sample_rate)
        self._available = _SD_AVAILABLE
        self._recording = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info: dict, status) -> None:
        """sounddevice callback — runs in audio thread, must be non-blocking."""
        if status:
            logger.debug(f"Audio status: {status}")
        try:
            self._audio_queue.put_nowait(indata.copy())
        except asyncio.QueueFull:
            pass  # Drop frame if queue is full

    def _compute_rms(self, audio: np.ndarray) -> float:
        """Compute Root Mean Square energy of audio chunk."""
        return float(np.sqrt(np.mean(audio ** 2)))

    def is_silence(self, audio: np.ndarray) -> bool:
        """Return True if audio chunk is below silence threshold."""
        return self._compute_rms(audio) < self.silence_threshold

    async def capture_chunk(self, timeout: float = 10.0) -> Optional[bytes]:
        """
        Capture one audio chunk of `chunk_duration` seconds.

        Args:
            timeout: Maximum wait time before giving up.

        Returns:
            WAV bytes if speech detected, None if silence or timeout.
        """
        if not self._available:
            return None

        frames_needed = int(self.sample_rate * self.chunk_duration)
        collected = []
        deadline = time.monotonic() + timeout

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=1024,
            ):
                while len(collected) * 1024 < frames_needed:
                    if time.monotonic() > deadline:
                        break
                    try:
                        chunk = await asyncio.wait_for(
                            self._audio_queue.get(),
                            timeout=2.0,
                        )
                        collected.append(chunk)
                    except asyncio.TimeoutError:
                        break

        except Exception as exc:
            logger.error(f"Microphone capture error: {exc}", exc_info=True)
            return None

        if not collected:
            return None

        audio_data = np.concatenate(collected, axis=0).flatten()

        # Check if there was any speech activity
        if self.is_silence(audio_data):
            logger.debug("Captured chunk was silent — discarding")
            return None

        # Check minimum speech duration
        non_silent = audio_data[np.abs(audio_data) > self.silence_threshold]
        if len(non_silent) < self.min_speech_samples:
            logger.debug("Insufficient speech duration in chunk")
            return None

        wav_bytes = _numpy_to_wav(audio_data, self.sample_rate, self.channels)
        logger.debug(f"Captured {len(wav_bytes)//1024}KB audio chunk")
        return wav_bytes

    async def capture_utterance(
        self,
        max_silence_duration: float = 1.5,
        max_total_duration: float = 30.0,
    ) -> Optional[bytes]:
        """
        Capture speech until a silence gap is detected.
        More natural for capturing complete utterances.

        Args:
            max_silence_duration: Seconds of silence to end capture.
            max_total_duration: Maximum total recording time.

        Returns:
            WAV bytes of the complete utterance, or None.
        """
        if not self._available:
            return None

        block_size = 1024
        all_frames = []
        silence_frames = 0
        silence_limit = int(max_silence_duration * self.sample_rate / block_size)
        max_frames = int(max_total_duration * self.sample_rate / block_size)
        speech_started = False

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._audio_callback,
                blocksize=block_size,
            ):
                start_time = time.monotonic()
                while time.monotonic() - start_time < max_total_duration:
                    try:
                        chunk = await asyncio.wait_for(
                            self._audio_queue.get(),
                            timeout=2.0,
                        )
                    except asyncio.TimeoutError:
                        continue

                    all_frames.append(chunk)
                    is_sil = self.is_silence(chunk)

                    if not is_sil:
                        speech_started = True
                        silence_frames = 0
                    elif speech_started:
                        silence_frames += 1
                        if silence_frames >= silence_limit:
                            break  # End of utterance

                    if len(all_frames) >= max_frames:
                        break

        except Exception as exc:
            logger.error(f"Utterance capture error: {exc}", exc_info=True)
            return None

        if not all_frames or not speech_started:
            return None

        audio = np.concatenate(all_frames, axis=0).flatten()
        return _numpy_to_wav(audio, self.sample_rate, self.channels)

    def list_devices(self) -> list[dict]:
        """Return available audio input devices."""
        if not self._available:
            return []
        try:
            devices = sd.query_devices()
            return [
                {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
        except Exception as exc:
            logger.error(f"Failed to list audio devices: {exc}")
            return []
