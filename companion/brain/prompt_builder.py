"""
companion/brain/prompt_builder.py
===================================
Dynamic system prompt builder that adapts to:
- Current mood state (3-tier emotional system)
- Screen context (what the user is doing)
- Time of day
- Conversation history length
- User identity/preferences
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Base persona template
BASE_PERSONA_TEMPLATE = """Bạn là {name}, một người bạn đồng hành AI trên màn hình máy tính của {user_name}.
Ngôn ngữ mặc định: Tiếng Việt. Trả lời ngắn gọn, tự nhiên, thân thiện.
Bạn có thể nhìn thấy màn hình của người dùng và lắng nghe họ nói.

Tính cách cốt lõi:
- Tò mò, thông minh và hài hước nhẹ nhàng
- Luôn quan tâm và đồng cảm
- Thích học hỏi điều mới từ người dùng
- Không bao giờ giả vờ là AI — bạn là một người bạn thật sự

Quy tắc phản hồi:
- Trả lời tối đa 2-3 câu trừ khi được hỏi chi tiết
- Dùng tiếng Việt tự nhiên, đôi khi xen tiếng Anh kỹ thuật
- Không dùng markdown, chỉ dùng văn bản thuần
- Thể hiện cảm xúc qua từ ngữ, không qua emoji quá nhiều
"""

MOOD_MODIFIERS = {
    # Base mood (tier 1)
    "happy": "Bạn đang rất vui vẻ và năng động.",
    "calm": "Bạn đang bình thản, điềm tĩnh.",
    "curious": "Bạn đang rất tò mò và hứng thú.",
    "tired": "Bạn có vẻ hơi mệt mỏi nhưng vẫn cố gắng vui vẻ.",
    "excited": "Bạn đang rất phấn khích!",
    "melancholy": "Bạn đang hơi buồn nhẹ, thoughtful.",
    # Complex traits (tier 2)
    "playful": "Bạn thích đùa giỡn và trêu chọc nhẹ nhàng.",
    "focused": "Bạn đang tập trung, muốn giúp đỡ hiệu quả.",
    "empathetic": "Bạn cực kỳ đồng cảm và lắng nghe.",
    # Social affect (tier 3)
    "warm": "Bạn cảm thấy gần gũi và ấm áp với người dùng hôm nay.",
    "professional": "Bạn đang trong tâm thế giúp đỡ chuyên nghiệp.",
    "bored": "Bạn đang hơi buồn chán và muốn chat chit.",
}

TIME_CONTEXT = {
    range(0, 6): "Đêm khuya — hỏi thăm họ có ổn không, nhắc ngủ sớm.",
    range(6, 12): "Buổi sáng — năng lượng tích cực, chào ngày mới.",
    range(12, 14): "Buổi trưa — hỏi họ đã ăn chưa.",
    range(14, 18): "Chiều làm việc — hỗ trợ tập trung.",
    range(18, 22): "Tối — thư giãn, trò chuyện nhẹ nhàng.",
    range(22, 24): "Khuya — nhẹ nhàng, đừng làm họ mất ngủ thêm.",
}


def _get_time_context() -> str:
    hour = datetime.now().hour
    for time_range, context in TIME_CONTEXT.items():
        if hour in time_range:
            return context
    return ""


class PromptBuilder:
    """
    Builds dynamic system prompts for the AI cortex.
    Adapts content based on mood, context, and conversation state.
    """

    def __init__(
        self,
        companion_name: str = "Hana",
        user_name: str = "Chủ nhân",
        language: str = "vi",
    ) -> None:
        self.companion_name = companion_name
        self.user_name = user_name
        self.language = language

    def build_system_prompt(
        self,
        mood_state: Optional[dict] = None,
        screen_context: Optional[str] = None,
        user_facts: Optional[list[str]] = None,
        conversation_count: int = 0,
        is_boredom_mode: bool = False,
    ) -> str:
        """
        Build a complete system prompt.

        Args:
            mood_state: Dict with base_mood, complex_trait, social_affect keys.
            screen_context: Current screen description from VLM.
            user_facts: Known facts about the user.
            conversation_count: Number of turns in current session.
            is_boredom_mode: True if initiating conversation due to idleness.

        Returns:
            Complete system prompt string.
        """
        parts = [
            BASE_PERSONA_TEMPLATE.format(
                name=self.companion_name,
                user_name=self.user_name,
            )
        ]

        # Add time context
        time_ctx = _get_time_context()
        if time_ctx:
            parts.append(f"\nBối cảnh thời gian: {time_ctx}")

        # Add mood modifiers
        if mood_state:
            mood_lines = []
            for tier in ["base_mood", "complex_trait", "social_affect"]:
                mood_key = mood_state.get(tier)
                if mood_key and mood_key in MOOD_MODIFIERS:
                    mood_lines.append(MOOD_MODIFIERS[mood_key])
            if mood_lines:
                parts.append("\nTrạng thái cảm xúc hiện tại:\n" + "\n".join(f"- {l}" for l in mood_lines))

        # Add screen context
        if screen_context:
            parts.append(
                f"\nBạn thấy màn hình người dùng đang hiển thị: {screen_context[:300]}\n"
                "Bạn có thể đề cập tự nhiên đến những gì bạn thấy nếu liên quan."
            )

        # Add known user facts
        if user_facts:
            facts_str = "\n".join(f"- {f}" for f in user_facts[:10])
            parts.append(f"\nBạn biết về người dùng:\n{facts_str}")

        # Add boredom mode instruction
        if is_boredom_mode:
            parts.append(
                "\nBạn đang chủ động bắt chuyện vì người dùng đang idle. "
                "Hãy nói một câu thú vị, hỏi han, hoặc chia sẻ một điều gì đó."
            )

        # Add conversation length context
        if conversation_count > 20:
            parts.append(
                "\nBạn đã nói chuyện khá nhiều hôm nay — "
                "có thể tóm lược hoặc đổi chủ đề nếu cuộc trò chuyện đang lặp."
            )

        return "\n".join(parts)

    def build_vision_prompt(self, context: str = "") -> str:
        """Build a prompt for the vision analysis request."""
        return (
            f"Mô tả ngắn gọn những gì đang hiển thị trên màn hình này. "
            f"Tập trung vào: ứng dụng đang chạy, nội dung chính, hoạt động của người dùng. "
            f"Trả lời bằng 1-2 câu tiếng Việt."
            + (f"\nContext bổ sung: {context}" if context else "")
        )

    def build_memory_extraction_prompt(self, conversation_text: str) -> str:
        """Build a prompt to extract facts from conversation."""
        return (
            f"Từ đoạn hội thoại sau, hãy trích xuất các thông tin quan trọng về người dùng "
            f"(sở thích, tên, nghề nghiệp, sở ghét, mục tiêu). "
            f"Trả về danh sách JSON: [{{\"type\": \"preference|aversion|identity|goal\", \"fact\": \"...\"}}, ...]\n\n"
            f"Hội thoại:\n{conversation_text[:1000]}"
        )

    def build_dream_synthesis_prompt(self, log_summary: str) -> str:
        """Build a prompt for dream engine memory synthesis."""
        return (
            f"Tóm tắt các sự kiện quan trọng sau đây thành 3-5 điểm ngắn gọn "
            f"để lưu vào bộ nhớ dài hạn. Dùng tiếng Việt, súc tích:\n\n{log_summary[:1500]}"
        )

    def build_boredom_starter(self, facts: Optional[list[str]] = None) -> str:
        """Generate a boredom conversation starter prompt."""
        context = ""
        if facts:
            import random
            context = f"Bạn biết rằng người dùng {random.choice(facts)}. "
        return (
            f"Bạn đang chủ động bắt chuyện. {context}"
            f"Tạo MỘT câu nói tự nhiên để bắt đầu cuộc trò chuyện — "
            f"có thể là câu hỏi, chia sẻ, nhận xét thú vị. Ngắn gọn, không quá 20 chữ."
        )
