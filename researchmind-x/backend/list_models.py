from google import genai

from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)
for m in client.models.list():
    if "lite" in m.name.lower():
        print(m.name)