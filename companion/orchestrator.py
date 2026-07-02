"""
companion/orchestrator.py
==========================
Central Asyncio Orchestrator of MyCompanion.
Manages Event Loops, priority queues, turn locks,
and coordinates all subcomponents (Brain, Senses, Memory, UI, Movement, Dream, Learning).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional
from pydantic_settings import BaseSettings
from PyQt6.QtWidgets import QApplication

from companion.utils.config import SystemConfig
from companion.utils.priority_queue import AsyncPriorityQueue, Priority, PrioritizedMessage
from companion.utils.turn_manager import TurnManager, TurnState
from companion.utils.event_bus import get_event_bus, EventType, Event
from companion.brain.cortex import AICortex
from companion.memory.memory_manager import MemoryManager
from companion.senses.vision_agent import VisionAgent
from companion.senses.stt_pipeline import STTPipeline
from companion.persona.mood_engine import MoodEngine
from companion.persona.dialogue_style import DialogueStyle
from companion.persona.boredom_protocol import BoredomProtocol
from companion.expression.expression_engine import ExpressionEngine
from companion.movement.movement_engine import MovementEngine
from companion.dream.dream_engine import DreamEngine
from companion.learning.auto_learner import AutoLearner
from companion.desktop.chat_widget import ChatWidget

# Try edge-tts (graceful fallbacks if offline/uninstalled)
try:
    import edge_tts
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False

logger = logging.getLogger(__name__)

class VisionConfig(BaseSettings):  # Hoặc BaseModel tùy cách bạn viết
    # ... các dòng code hiện có của bạn ...
    
    # Thêm hai dòng này vào:
    max_width: int = 1920
    max_height: int = 1080
    
class AsyncioOrchestrator:
    """
    Main system coordinator running on single asyncio loop.
    Controls execution locks and message priority queues.
    """

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self.queue = AsyncPriorityQueue()
        self.turn_manager = TurnManager()
        self._bus = get_event_bus()
        self._running = False
        self._tasks: list[asyncio.Task] = []

        # 1. UI Setup
        self.widget = ChatWidget(config.ui.window_width, config.ui.window_height)
        self.widget.move(config.ui.initial_x, config.ui.initial_y)
        self.widget.show()

        # 2. Components declaration
        self.memory = MemoryManager(config.db_path)
        self.cortex = AICortex.from_config(config)
        self.mood_engine = MoodEngine()

        # Senses
        self.vision = VisionAgent(
            capture_interval=config.vision.capture_interval,
            max_width=config.vision.max_width,
            max_height=config.vision.max_height,
            jpeg_quality=config.vision.jpeg_quality,
            vlm_fn=self._run_vlm
        )
        self.stt = STTPipeline(
            sample_rate=config.audio.stt_sample_rate,
            chunk_duration=config.audio.stt_chunk_duration,
            silence_threshold=config.audio.stt_silence_threshold,
            transcribe_fn=self._run_whisper
        )

        # Expression - DISABLED (No VTube Studio)
        # self.vts = ExpressionEngine(config.vts.host, config.vts.port)
        self.vts = None  # VTube Studio removed - using caption_server instead

        # Movement - DISABLED (No avatar movement needed)
        # self.movement = MovementEngine(self.widget, config.idle.movement_idle_threshold)
        self.movement = None  # Movement engine removed for lightweight desktop companion

        # Dream Engine
        self.dream = DreamEngine(
            db_conn=None,  # Configured after memory init
            get_logs_fn=self._get_daily_logs,
            synthesis_fn=self._run_synthesis,
            save_fact_fn=self._save_fact,
            dream_idle_threshold=config.idle.dream_idle_threshold,
            cycle_duration=config.idle.dream_cycle_duration
        )

        # Auto Learner
        self.learner = AutoLearner(
            save_fact_fn=self._save_fact,
            llm_extract_fn=self._run_fact_extraction
        )

        # Boredom Protocol
        self.boredom = BoredomProtocol(config.idle.boredom_idle_threshold)

        # Connect signals
        self.widget.text_submitted.connect(self._on_widget_text)
        self._bus.subscribe(EventType.USER_VOICE_INPUT, self._on_voice_input)
        self._bus.subscribe(EventType.SCREEN_CONTEXT_UPDATED, self._on_screen_context)
        self._bus.subscribe(EventType.BOREDOM_TRIGGERED, self._on_boredom_triggered)

    async def start(self) -> None:
        """Initialize databases and launch all background service loops."""
        logger.info("Initializing Orchestrator core layers...")
        self._running = True

        # 1. Initialize Memory Manager
        await self.memory.initialize()
        self.dream.db = self.memory._conn  # Share db connection

        # 2. Initialize Cortex
        await self.cortex.initialize()

        # 3. Start auto-learner and background modules
        await self.learner.start()
        await self.boredom.start()

        if self.config.enable_vision:
            await self.vision.start()
        if self.config.enable_stt:
            await self.stt.start()
        # VTS and Movement disabled - no avatar system
        # if self.config.enable_vts:
        #     await self.vts.start()
        # if self.config.enable_movement:
        #     await self.movement.start()

        await self.dream.start()

        # 4. Main queue processing task
        self._tasks.append(asyncio.create_task(self._process_queue_loop(), name="queue_processor"))

        # Welcome message
        self.widget.append_assistant_response("Xin chào! Mình đã khởi động xong rồi nè~ 💜")
        logger.info("Orchestrator successfully online.")

    async def stop(self) -> None:
        """Clean shutdown of all subsystems."""
        self._running = False
        for t in self._tasks:
            t.cancel()
        
        await self.vision.stop()
        await self.stt.stop()
        # VTS and Movement disabled
        # await self.vts.stop()
        # await self.movement.stop()
        await self.dream.stop()
        await self.learner.stop()
        await self.boredom.stop()

        await self.cortex.shutdown()
        await self.memory.shutdown()
        logger.info("Orchestrator offline.")

    # Core callback adapters
    async def _run_vlm(self, image_bytes: bytes) -> Optional[str]:
        return await self.cortex.analyze_screen(image_bytes)

    async def _run_whisper(self, audio_bytes: bytes, lang: str) -> Optional[str]:
        return await self.cortex.transcribe_audio(audio_bytes, language=lang)

    async def _run_synthesis(self, text: str) -> Optional[str]:
        return await self.cortex.synthesize_memory(text)

    async def _run_fact_extraction(self, text: str) -> Optional[str]:
        return await self.cortex.extract_facts(text)

    async def _save_fact(self, f_type: str, content: str, conf: float = 0.8, src: str = "orchestrator") -> bool:
        return await self.memory.facts.add_fact(f_type, content, conf, src)

    async def _get_daily_logs(self) -> list[dict]:
        return await self.memory.conversations.get_all_today()

    # Event adapters feeding the PriorityQueue
    def _on_widget_text(self, text: str) -> None:
        # Movement disabled - no avatar tracking needed
        # self.movement.update_interaction_time()
        self.queue.put_nowait(
            Priority.USER_TEXT,
            message=text,
            source="widget_text"
        )

    async def _on_voice_input(self, event: Event) -> None:
        # Movement disabled
        # self.movement.update_interaction_time()
        # Feed PyQt6 layout
        self.widget.chat_log.append_message("Bạn (nói)", str(event.data), is_user=True)
        await self.queue.put(
            Priority.VOICE,
            message=str(event.data),
            source="stt_pipeline"
        )

    async def _on_screen_context(self, event: Event) -> None:
        await self.queue.put(
            Priority.SCREEN,
            message=str(event.data),
            source="vision_agent"
        )

    async def _on_boredom_triggered(self, event: Event) -> None:
        await self.queue.put(
            Priority.BOREDOM,
            message="Chủ động nói chuyện",
            source="boredom_protocol"
        )

    # Queue consumer loops
    async def _process_queue_loop(self) -> None:
        while self._running:
            try:
                # Wait for next priority item
                item = await self.queue.get()
                logger.debug(f"Processing queued task level [{item.priority}] from '{item.source}'")
                
                # Execute inside absolute Turn Lock gate to prevent overlap
                async with self.turn_manager.acquire_turn(TurnState.AI_THINKING, holder=item.source):
                    await self._handle_item(item)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error processing queue item: {exc}", exc_info=True)

    async def _handle_item(self, item: PrioritizedMessage) -> None:
        # Load known context parameters for prompt build
        context = await self.memory.get_context_for_prompt()
        screen_context = self.vision.last_context

        response = None
        is_proactive = False

        if item.priority in (Priority.USER_TEXT, Priority.VOICE):
            # Direct User response
            await self.memory.log_user_message(item.message)
            
            response = await self.cortex.think(
                user_message=item.message,
                conversation_history=context["history"],
                mood_state=self.mood_engine.get_mood_state(),
                screen_context=screen_context,
                user_facts=context["facts"]
            )
            self.mood_engine.update_from_interaction(item.message, "neutral")

        elif item.priority == Priority.SCREEN:
            # Context reactive remark (only if mood is curious or bored)
            mood = self.mood_engine.get_mood_state()
            if mood["base_mood"] in ("curious", "excited") and time.monotonic() - self.stt.last_activity > 30.0:
                response = await self.cortex.think(
                    user_message=f"Bình luận ngắn về những gì đang diễn ra trên màn hình: {item.message}",
                    conversation_history=context["history"],
                    mood_state=mood,
                    screen_context=screen_context,
                    user_facts=context["facts"]
                )

        elif item.priority == Priority.BOREDOM:
            # Boredom conversation starter
            is_proactive = True
            response = await self.cortex.think(
                user_message="Bắt chuyện ngắn với người dùng vì họ đã lâu không nói gì.",
                conversation_history=context["history"],
                mood_state=self.mood_engine.get_mood_state(),
                screen_context=screen_context,
                user_facts=context["facts"],
                is_boredom=True
            )

        if response:
            # Post process dialogue style based on emotional markers
            styled_text = DialogueStyle.style_response(response, self.mood_engine.get_mood_state())
            
            # Save assistant log
            await self.memory.log_assistant_message(styled_text)
            
            # Write to UI widget (primary output - no VTS avatar)
            self.widget.append_assistant_response(styled_text)
            
            # Send to caption server for OBS overlay (optional)
            # await self._bus.publish(Event(EventType.CAPTION_UPDATE, data=styled_text, source="orchestrator"))
            
            # Play aloud via TTS if configured
            if self.config.enable_tts:
                await self._speak_tts(styled_text)

    async def _speak_tts(self, text: str) -> None:
        """Synthesize and play audio output via edge-tts and local mpv/paplay."""
        if not _TTS_AVAILABLE:
            return

        async with self.turn_manager.acquire_turn(TurnState.TTS_SPEAKING, holder="tts_playback"):
            try:
                await self._bus.publish(Event(EventType.TTS_START, source="tts_engine"))
                
                # Generate audio bytes asynchronously
                communicate = edge_tts.Communicate(text, self.config.audio.tts_voice)
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]

                # Write temp wav
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as fp:
                    fp.write(audio_data)
                    temp_path = fp.name

                # Play via process (Arch Linux compatible)
                player = self.config.audio.tts_player
                proc = await asyncio.create_subprocess_exec(
                    player, temp_path,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
                
                # Cleanup temp file
                import os
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            except Exception as exc:
                logger.error(f"TTS playback failed: {exc}")
            finally:
                await self._bus.publish(Event(EventType.TTS_END, source="tts_engine"))
