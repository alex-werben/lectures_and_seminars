import time
import logging

try:
    from ddgs import DDGS
except ImportError as e:
    raise ImportError(
        "Пожалуйста, установите библиотеку: pip install duckduckgo-search"
    ) from e

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 15, region: str = "ru-ru") -> str:
    """Выполняет веб-поиск по заданному запросу и возвращает результаты."""
    logger.info(f"🔎 Выполняется веб-поиск по запросу: '{query}'")
    try:
        with DDGS(timeout=60) as ddgs:
            # Небольшая задержка для обхода rate-limit
            time.sleep(3)
            results = list(ddgs.text(query, max_results=max_results, region=region))
        if not results:
            logger.warning(f"Поиск по запросу '{query}' не дал результатов")
            return "Поиск не дал результатов."

        formatted_results = "\n---\n".join(
            [f"Результат {i + 1}: {r}" for i, r in enumerate(results)]
        )
        logger.info(f"✅ Найдено {len(results)} результатов для запроса '{query}'")
        return formatted_results
    except Exception as e:
        error_msg = f"Ошибка при выполнении поиска: {e}"
        logger.error(error_msg)
        return error_msg
