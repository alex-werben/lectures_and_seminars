import os
import json
import arxiv
import asyncio
import logging

from datetime import datetime
from typing import List, Dict, Optional
from mcp.server.fastmcp import FastMCP, Context


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arxiv_assistant")

PAPER_DIR = "papers"
os.makedirs(
    name=PAPER_DIR, 
    exist_ok=True
)

PAPER_INDEX = {}

mcp = FastMCP(
    name="llm_research",
    system_prompt="""
Ты - помощник для анализа научных статей по LLM и Computer Science. 
Используй инструменты для поиска и анализа статей. 
Отвечай на русском языке.
"""
)

def load_paper_index():
    """
    Загрузка глобального индекса статей.
    """
    global PAPER_INDEX
    index_path = os.path.join(PAPER_DIR, "index.json")
    
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                PAPER_INDEX = json.load(f)

            logger.info(f"Загружен индекс {len(PAPER_INDEX)} статей")
        except Exception as e:
            logger.error(f"Ошибка загрузки индекса: {str(e)}")
    else:
        PAPER_INDEX = {}

def save_paper_index():
    """
    Сохранение глобального индекса статей.
    """
    index_path = os.path.join(PAPER_DIR, "index.json")

    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(PAPER_INDEX, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения индекса: {str(e)}")

def paper_to_dict(paper: arxiv.Result) -> Dict:
    """
    Конвертация объекта статьи в словарь.
    """
    return {
        'id': paper.get_short_id(),
        'title': paper.title,
        'authors': [author.name for author in paper.authors],
        'summary': paper.summary,
        'pdf_url': paper.pdf_url,
        'published': str(paper.published.date()),
        'primary_category': paper.primary_category,
        'categories': paper.categories,
        'comment': paper.comment,
        'links': [link.href for link in paper.links]
    }

@mcp.tool()
async def search_papers(context: Context,
                        topic: str, 
                        max_results: int = 10) -> List[str]:
    """
    Поиск свежих статей на arXiv по теме LLM и Computer Science.
    """
    load_paper_index()
    
    loop = asyncio.get_running_loop()
    
    try:
        papers = await loop.run_in_executor(
            None, 
            lambda: list(arxiv.Client().results(
                arxiv.Search(
                    query=f"{topic} AND (cat:cs.* OR cat:cs.CL)",
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                    sort_order=arxiv.SortOrder.Descending
                )
            ))
        )
        
        new_papers = []

        for paper in papers:
            paper_id = paper.get_short_id()
            paper_data = paper_to_dict(paper)
            
            if paper_id not in PAPER_INDEX:
                PAPER_INDEX[paper_id] = paper_data
                new_papers.append(paper_id)
        
        save_paper_index()
        logger.info(f"Найдено {len(papers)} статей, новых: {len(new_papers)}")
        
        return [p.get_short_id() for p in papers]
    
    except Exception as e:
        logger.error(f"Ошибка поиска статей: {str(e)}")

        return []

@mcp.tool()
async def get_paper_details(context: Context,
                            paper_id: str) -> Dict:
    """
    Получение информации о статье по её ID.
    """
    load_paper_index()
    
    if paper_id in PAPER_INDEX:
        return PAPER_INDEX[paper_id]
    
    try:
        loop = asyncio.get_running_loop()
        search = arxiv.Search(id_list=[paper_id])
        paper = next(loop.run_in_executor(None, lambda: list(arxiv.Client().results(search))))
        
        paper_data = paper_to_dict(paper)
        PAPER_INDEX[paper_id] = paper_data
        save_paper_index()
        
        return paper_data
    except Exception:
        return {
            "error": f"Статья с ID {paper_id} не найдена"
        }

@mcp.tool()
async def analyze_trends(context: Context,
                         topics: List[str], 
                         years: Optional[List[int]] = None) -> Dict:
    """
    Анализ трендов по темам за указанные годы.
    """
    load_paper_index()
    
    if years is None:
        current_year = datetime.now().year
        years = list(range(current_year - 5, current_year + 1))
    
    trends = {
        topic: {year: 0 for year in years} for topic in topics
    }
    
    for _, details in PAPER_INDEX.items():
        pub_year = int(details['published'].split('-')[0])
        
        for topic in topics:
            content = f"{details['title']} {details['summary']}".lower()

            if topic.lower() in content and pub_year in years:
                trends[topic][pub_year] += 1
    
    return trends

@mcp.tool()
async def find_related_papers(context: Context,
                              paper_id: str,
                              max_results: int = 5) -> List[str]:
    """
    Найти похожие статьи по ID исходной статьи.
    """
    load_paper_index()
    
    if paper_id not in PAPER_INDEX:
        return []
    
    source_paper = PAPER_INDEX[paper_id]
    source_title = source_paper['title'].lower()
    
    keywords = set(source_title.split()[:5])
    
    related = []
    for pid, paper in PAPER_INDEX.items():
        if pid == paper_id:
            continue
            
        title_words = set(paper['title'].lower().split())
        common = keywords & title_words
        
        if common:
            related.append(
                {
                    "id": pid,
                    "title": paper['title'],
                    "score": len(common),
                    "common_keywords": list(common)
                }
            )
    
    related.sort(key=lambda x: x['score'], reverse=True)

    return [item['id'] for item in related[:max_results]]

@mcp.resource("papers://index")
async def list_all_papers() -> str:
    """
    Список всех статей в системе.
    """
    load_paper_index()
    
    content = "## Все статьи в системе\n\n"

    if not PAPER_INDEX:
        content += "База статей пуста. Используйте search_papers для поиска."

        return content
    
    for paper_id, details in list(PAPER_INDEX.items())[:50]:
        content += f"### {details['title']}\n"
        content += f"- **ID**: {paper_id}\n"
        content += f"- **Авторы**: {', '.join(details['authors'][:3])}\n"
        content += f"- **Опубликовано**: {details['published']}\n\n"
    
    if len(PAPER_INDEX) > 50:
        content += f"\nПоказано 50 из {len(PAPER_INDEX)} статей\n"
    
    return content

@mcp.resource("papers://recent")
async def get_recent_papers() -> str:
    """
    Последние добавленные статьи.
    """
    load_paper_index()
    
    if not PAPER_INDEX:
        return "База статей пуста. Используйте search_papers для поиска."
    
    sorted_papers = sorted(
        PAPER_INDEX.items(),
        key=lambda x: x[1]['published'],
        reverse=True
    )[:10]
    
    content = "## Последние добавленные статьи\n\n"
    
    for paper_id, details in sorted_papers:
        content += f"### {details['title']}\n"
        content += f"- **ID**: {paper_id}\n"
        content += f"- **Дата**: {details['published']}\n"
        content += f"- **Категории**: {', '.join(details['categories'][:3])}\n\n"
    
    return content

if __name__ == "__main__":
    load_paper_index()
    
    mcp.run(transport='stdio')