"""
MyCompanion — AI Desktop Companion Framework
============================================
A lightweight, async-first AI companion for Arch Linux GNOME.
All inference is offloaded to cloud APIs (Groq, OpenAI, Anthropic).
Local footprint is strictly kept under 300MB RAM.

Architecture: Event-driven AsyncioOrchestrator with PriorityQueue.
"""

__version__ = "1.0.0"
__author__ = "MyCompanion Contributors"
__license__ = "Personal Use Only (see model_setup/attribution.py)"
