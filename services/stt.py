import io
from openai import AsyncOpenAI
from config import settings

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def transcribe(audio_bytes: io.BytesIO) -> str:
    audio_bytes.seek(0)
    audio_bytes.name = "audio.ogg"
    transcript = await _client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bytes,
        language="ru",
    )
    return transcript.text.strip()
