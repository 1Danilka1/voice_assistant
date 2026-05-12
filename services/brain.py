from datetime import datetime
import pytz
import anthropic
from config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Tool schema — Claude fills this on every voice command
_PARSE_TOOL = {
    "name": "parse_command",
    "description": "Разбери голосовую команду пользователя и верни структурированные данные",
    "input_schema": {
        "type": "object",
        "required": ["intent", "reply"],
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "create_note",
                    "view_notes",
                    "view_note",
                    "delete_note",
                    "search_notes",
                    "create_event",
                    "view_events",
                    "delete_event",
                    "send_message",
                    "add_contact",
                    "view_contacts",
                    "navigate",
                    "stream_capture",
                    "time_capsule",
                    "mood_note",
                    "unknown",
                ],
            },
            # note fields
            "title": {"type": "string"},
            "text": {"type": "string"},
            # event fields
            "datetime_start": {
                "type": "string",
                "description": "ISO 8601 с часовым поясом, например 2025-06-01T15:00:00+03:00",
            },
            "datetime_end": {"type": "string"},
            "reminder_minutes": {
                "type": "integer",
                "description": "За сколько минут до события напомнить (по умолчанию 30)",
            },
            # messaging
            "recipient": {"type": "string", "description": "Имя получателя из контактов"},
            "message_text": {
                "type": "string",
                "description": "Готовое, полное сообщение для отправки (не фрагмент)",
            },
            # search / navigation
            "query": {"type": "string"},
            "page": {
                "type": "string",
                "enum": ["home", "notes", "calendar", "contacts", "mood"],
            },
            # time capsule
            "reveal_date": {
                "type": "string",
                "description": "ISO 8601 — когда открыть капсулу",
            },
            # mood
            "mood_text": {"type": "string", "description": "Описание настроения своими словами"},
            "mood_score": {
                "type": "integer",
                "description": "Оценка настроения 1 (ужасно) … 5 (отлично)",
            },
            # event list filter
            "date_filter": {
                "type": "string",
                "enum": ["today", "week", "all"],
            },
            # stream_capture — список извлечённых элементов
            "items": {
                "type": "array",
                "description": "Для stream_capture: элементы, извлечённые из свободной речи",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["note", "event", "task", "idea"],
                        },
                        "title": {"type": "string"},
                        "text": {"type": "string"},
                        "datetime": {"type": "string"},
                    },
                    "required": ["type", "title"],
                },
            },
            "reply": {
                "type": "string",
                "description": "Короткий ответ пользователю на русском (1–2 предложения)",
            },
        },
    },
}

_SYSTEM = """\
Ты — умный интерпретатор голосовых команд персонального ассистента.
Пользователь говорит на русском языке. Всегда отвечай ТОЛЬКО через инструмент parse_command.

Правила:
• Для datetime используй ISO 8601 с часовым поясом {tz}.
• Если дата не указана явно, выбирай разумный default (сегодня/завтра).
• Если время не указано, ставь 12:00.
• Для end_dt добавляй +1 час к start_dt, если не сказано иначе.
• Для send_message → message_text должен быть полным, готовым к отправке сообщением
  (вежливым, в естественном стиле). Дополни фрагменты пользователя.
• Для stream_capture распредели каждую мысль по типам: note/event/task/idea.
• mood_score: 5=отлично, 4=хорошо, 3=нейтрально, 2=плохо, 1=ужасно — угадай из текста.
• reply — дружелюбный краткий ответ.

Сейчас: {now}
"""


async def parse_intent(text: str) -> dict:
    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M, %A")
    system = _SYSTEM.format(tz=settings.TIMEZONE, now=now)

    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system,
        tools=[_PARSE_TOOL],
        tool_choice={"type": "tool", "name": "parse_command"},
        messages=[{"role": "user", "content": text}],
    )

    if response.stop_reason == "max_tokens":
        return {"intent": "unknown", "reply": "Голосовое сообщение слишком длинное — попробуй разбить на части."}

    for block in response.content:
        if block.type == "tool_use":
            return block.input

    return {"intent": "unknown", "reply": "Не понял команду, попробуй ещё раз."}
