import logging

import aiohttp

from config import GEMINI_API_KEY, GEMINI_MODEL
from database.cache import clear_conversation_history
from database.cache import get_conversation_history as db_get_conversation_history
from database.cache import save_conversation

logger = logging.getLogger(__name__)

async def get_gemini_response(prompt: str) -> str | None:
    api_url = "https://ia.lionelmelo.qzz.io/api/lionel9b"
    params = {"q": prompt}
    request_timeout = aiohttp.ClientTimeout(total=45)

    try:
        async with aiohttp.ClientSession(timeout=request_timeout) as session:
            async with session.get(api_url, params=params) as resp:
                if resp.status != 200:
                    logger.error("Lionel API returned status %s: %s", resp.status, await resp.text())
                    return None

                content = await resp.text()
                # On essaie de parser en JSON si c'est du JSON
                try:
                    import json
                    data = json.loads(content)
                    # L'API peut renvoyer {"response": "..."} ou simulaire
                    for key in ["response", "answer", "message", "reply", "text", "result"]:
                        if key in data and isinstance(data[key], str):
                            return data[key]
                    
                    # Si aucun de ces mots cles, retourner la 1ere string trouvee
                    for val in data.values():
                        if isinstance(val, str):
                            return val
                    
                    return content.strip()
                except ValueError:
                    # Si ce n'est pas du JSON, c'est que la reponse est en texte brut
                    return content.strip()
    except aiohttp.ClientError as exc:
        logger.error("Lionel API request failed: %s", exc)
        return None


def get_conversation_history(user_id: int, limit: int = 5) -> str:
    return db_get_conversation_history(user_id, limit)


def save_conversation_message(user_id: int, role: str, content: str) -> None:
    save_conversation(user_id, role, content)


def clear_history(user_id: int) -> None:
    clear_conversation_history(user_id)
