# Project Progress

- [x] Initialize `progress.md` file.
- [x] Read `README.md` and extract key information about the project architecture, lifecycle, and setup.
- [x] Read `companion/orchestrator.py` to understand the core control flow.
- [x] Read `companion/__init__.py`, `companion/orchestrator.py` and `companion/main.py`
- [x] Summarize project into `progress.md` with project name, goals, current achievements, future tasks, and known bugs.
- [ ] Update `progress.md` to reflect the new Live2D model setup and future development/bug fixing.

## Project Name

MyCompanion Framework

## Project Goals

To provide a lightweight, asyncio-first AI desktop companion for Arch Linux GNOME, running entirely locally (except for AI inference offloaded to cloud APIs). It aims to be highly optimized for minimal hardware configurations (e.g., AMD Ryzen 3, AMD Radeon Onboard, 8GB RAM).

## Current Achievements

- **Core Architecture:** Established an event-driven `AsyncioOrchestrator` with a `PriorityQueue` for managing various sub-components.
- **AI Integration:** Implemented an `AICortex` for AI inference, utilizing Groq Llama 3 with fallback to OpenAI/Anthropic APIs.
- **Sensory Input:** Developed `VisionAgent` for screen capture and `STTPipeline` for voice input (Whisper STT).
- **User Interface:** Integrated a PyQt6-based `ChatWidget` for interaction.
- **Memory Management:** `MemoryManager` is in place for logging conversations and storing facts.
- **Idle Protocols:** `DreamEngine` for daily log synthesis and `BoredomProtocol` for proactive engagement are implemented.
- **Movement & Expression:** `MovementEngine` and `ExpressionEngine` (for VTS WebSocket) are integrated to control the companion's presence and reactions.
- **Learning:** `AutoLearner` is in place for fact extraction.
- **Setup:** Clear setup instructions are provided for Arch Linux, including system package installation, Python dependencies, and API key configuration.

## Future Tasks

- Integrate the new Live2D model (from Behance link provided: `https://www.behance.net/gallery/246204933/LIVE2D-COMMISSION-LIVE2D-MODEL2D-VTUBER-MODEL?tracking_source=search_projects|vtuber+model+free&l=0`) into the project as the default model, replacing or updating existing references.
- Continue project development based on the core goals, focusing on enhancing existing features and potentially adding new ones.
- Actively identify and fix any bugs that arise during development and testing.
- Regularly update `progress.md` to reflect all development efforts, bug fixes, and new features.
- Enhance `DreamEngine` for more sophisticated memory synthesis.
- Improve `AutoLearner` for deeper and more varied fact extraction methods.
- Expand `DialogueStyle` and `MoodEngine` for richer emotional expressions and conversational nuances.
- Optimize performance further for even lower-end hardware configurations.
- Explore additional sensory inputs and interaction modalities.
- Implement more robust error handling and logging mechanisms.
- Develop comprehensive testing suite for all components.

## Known Bugs

- No specific bugs are explicitly documented in the initial review of `README.md`, `companion/__init__.py`, `companion/orchestrator.py`, or `main.py`. Further code review and testing would be required to identify potential issues.