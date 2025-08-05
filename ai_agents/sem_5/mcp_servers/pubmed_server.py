import os
import json
import logging

from pymed import PubMed
from typing import Dict, List, Any
from googletrans import Translator
from mcp.server.fastmcp import FastMCP, Context


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medical_assistant")
logger.setLevel(logging.INFO)

pubmed = PubMed(
    tool="MedicalAssistant", 
    email="your@mail.ru"
)

translator = Translator()

MEDICAL_DIR = "medical_articles"
os.makedirs(
    name=MEDICAL_DIR, 
    exist_ok=True
)

mcp = FastMCP(
    name="Медицинский ассистент",
    instructions="""
Ты - медицинский ассистент, помогающий врачам и исследователям находить актуальную научную информацию.
Используй PubMed для поиска медицинских статей и предоставляй точные, проверенные данные.

Правила:
1. Всегда переводи медицинские термины и запросы на английский для поиска в PubMed
2. Сохраняй найденные статьи в локальную базу для быстрого доступа
3. Отвечай на русском языке, адаптируя сложную информацию для понимания
4. Всегда указывай источники информации (PMID статей)
5. Для обобщения информации используй несколько релевантных статей

Инструменты:
- search_medical_articles: Поиск статей в PubMed по медицинской теме
- get_article_details: Получение полной информации о статье
- summarize_medical_evidence: Обобщение данных из нескольких статей
""",
    lang="ru"
)

@mcp.tool()
def translate_medical_query(query: str, 
                            context: Context) -> str:
    """
    Перевод медицинского запроса с русского на английский для PubMed.
    
    Args:
        query (str): медицинский запрос на русском
        context (Context): контекст выполнения
    Returns:
        translated_query (str): переведенный запрос на английском
    """
    try:
        translation = translator.translate(
            text=query, 
            src='ru', 
            dest='en'
        )

        return translation.text
    except Exception as e:
        logger.error(f"Ошибка перевода: {str(e)}")

        return query

@mcp.tool()
def search_medical_articles(topic: str, 
                            max_results: int = 10,
                            context: Context = None) -> List[Dict]:
    """
    Поиск медицинских статей в PubMed по заданной теме.
    
    Args:
        topic (str): медицинская тема для поиска (на русском или английском)
        max_results (int): количество возвращаемых результатов
        context (Context): контекст выполнения
    Returns:
        articles (List[Dict]): список статей с базовой информацией
    """
    try:
        if any(cyr in topic for cyr in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
            topic = translate_medical_query(topic, context)
        
        results = pubmed.query(
            query=topic, 
            max_results=max_results
        )
        
        articles = []

        for article in results:
            article_id = article.pubmed_id.split('\n')[0]
            article_data = {
                'pmid': article_id,
                'title': article.title,
                'abstract': article.abstract,
                'authors': [f"{author['lastname']} {author['initials']}" for author in article.authors],
                'journal': article.journal,
                'publication_date': str(article.publication_date),
                'doi': article.doi,
                'keywords': article.keywords
            }

            articles.append(article_data)
            save_article(article_data)
        
        logger.info(f"Найдено {len(articles)} статей по теме: {topic}")

        return articles
    except Exception as e:
        logger.error(f"Ошибка поиска статей: {str(e)}")

        return [
            {
                "error": "Не удалось выполнить поиск. Проверьте запрос."
            }
        ]

def save_article(article: Dict):
    """
    Сохранение статьи в локальную базу данных.
    """
    try:
        topic_dir = article['keywords'][0].lower() if article.get('keywords') else "general"
        topic_dir = topic_dir.replace(" ", "_")
        dir_path = os.path.join(MEDICAL_DIR, topic_dir)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, f"{article['pmid']}.json")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(article, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения статьи: {str(e)}")

@mcp.tool()
def get_article_details(pmid: str, 
                        context: Context = None) -> Dict:
    """
    Получение полной информации о медицинской статье по PMID.
    
    Args:
        pmid (str): PubMed ID статьи
        context (Context): контекст выполнения
    Returns:
        article (Dict): полная информация о статье
    """
    try:
        for topic_dir in os.listdir(MEDICAL_DIR):
            dir_path = os.path.join(MEDICAL_DIR, topic_dir)
            file_path = os.path.join(dir_path, f"{pmid}.json")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        article = pubmed.get_article(pmid)

        article_data = {
            'pmid': pmid,
            'title': article.title,
            'abstract': article.abstract,
            'authors': [f"{author['lastname']} {author['initials']}" for author in article.authors],
            'journal': article.journal,
            'publication_date': str(article.publication_date),
            'doi': article.doi,
            'keywords': article.keywords,
            'methods': article.methods,
            'conclusions': article.conclusions,
            'results': article.results
        }
        save_article(article_data)

        return article_data
    except Exception as e:
        logger.error(f"Ошибка получения статьи {pmid}: {str(e)}")

        return {
            "error": f"Статья с PMID {pmid} не найдена"
        }

@mcp.tool()
def summarize_medical_evidence(pmids: List[str], 
                               context: Context = None) -> str:
    """
    Обобщение информации из нескольких медицинских статей.
    
    Args:
        pmids (List[str]): список PubMed ID статей
        context (Context): контекст выполнения
    
    Returns:
        summary (str): обобщенная информация на русском
    """
    try:
        articles = []

        for pmid in pmids:
            article = get_article_details(pmid, context)

            if 'error' not in article:
                articles.append(article)
        
        if not articles:
            return "Не найдено статей для обобщения"
        
        prompt = f"Обобщи следующие медицинские исследования на русском языке:\n\n"
        
        for i, article in enumerate(articles[:3]):
            prompt += f"Исследование #{i+1} (PMID: {article['pmid']}):\n"
            prompt += f"Заголовок: {article['title']}\n"
            prompt += f"Выводы: {article.get('conclusions', article.get('abstract', ''))}\n\n"
        
        prompt += "Основные выводы и клиническая значимость:"
        
        response = context.llm_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        
        summary = response.content.strip()
        
        refs = ", ".join([f"PMID:{art['pmid']}" for art in articles])
        summary += f"\n\nИсточники: {refs}"
        
        return summary
    except Exception as e:
        logger.error(f"Ошибка обобщения: {str(e)}")

        return "Не удалось обобщить информацию"

@mcp.prompt()
def handle_medical_query(prompt: str, 
                         context: Context) -> List[Dict[str, Any]]:
    """
    Обработчик медицинских запросов на русском языке.
    
    Логика:
    1. Анализ запроса и определение необходимости поиска
    2. Поиск релевантных статей в PubMed
    3. Обобщение информации из топ-статей
    4. Формирование ответа на русском языке
    
    Args:
        prompt (str): запрос пользователя
        context (Context): контекст выполнения
    
    Returns:
        messages (List[Dict]): список сообщений для ответа
    """
    try:
        articles = search_medical_articles(prompt, max_results=5, context=context)
        
        if not articles or 'error' in articles[0]:
            return [
                {
                    "role": "assistant",
                    "content": "🔍 Не удалось найти статьи по вашему запросу. Уточните тему поиска."
                }
            ]
        
        pmids = [art['pmid'] for art in articles[:3]]
        
        summary = summarize_medical_evidence(pmids, context)
        
        response = f"📚 По вашему запросу '{prompt}' найдено {len(articles)} статей:\n\n"
        response += f"{summary}\n\n"
        response += "Для более детальной информации вы можете запросить конкретную статью по её PMID."
        
        return [
            {
                "role": "assistant", 
                "content": response
            }
        ]
    
    except Exception as e:
        logger.exception("Ошибка обработки медицинского запроса")
        return [
            {
                "role": "assistant",
                "content": "⚠️ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте переформулировать вопрос."
            }
        ]

@mcp.resource("med://topics")
def list_medical_topics() -> str:
    """
    Возвращает список медицинских тем с сохраненными статьями.
    
    Returns:
        content (str): отформатированный список тем
    """
    topics = []

    for item in os.listdir(MEDICAL_DIR):
        item_path = os.path.join(MEDICAL_DIR, item)

        if os.path.isdir(item_path) and os.listdir(item_path):
            topics.append(item.replace("_", " ").title())
    
    content = "Доступные медицинские темы\n\n"

    if topics:
        content += "\n".join(f"- {topic}" for topic in sorted(topics))
        content += "\n\nИспользуйте команду @topic для поиска по теме"
    else:
        content += "База статей пуста. Начните с поиска медицинских статей."
    
    return content

@mcp.resource("med://article/{pmid}")
def get_formatted_article(pmid: str) -> str:
    """
    Возвращает отформатированную статью по PMID.
    
    Args:
        pmid (str): PubMed ID статьи
    Returns:
        content (str): отформатированное содержание статьи
    """
    article = get_article_details(pmid)
    
    if 'error' in article:
        return f"Статья с PMID {pmid} не найдена"
    
    content = f"# {article['title']}\n\n"
    content += f"**Авторы:** {', '.join(article['authors'])}\n\n"
    content += f"**Журнал:** {article['journal']} ({article['publication_date']})\n\n"
    content += f"**DOI:** {article.get('doi', 'N/A')}\n\n"
    content += "## Аннотация\n\n"
    content += f"{article['abstract']}\n\n"
    
    if article.get('conclusions'):
        content += "## Основные выводы\n\n"
        content += f"{article['conclusions']}\n\n"
    
    content += f"`PMID: {pmid}`"
    
    return content


if __name__ == "__main__":
    mcp.run(transport="stdio")