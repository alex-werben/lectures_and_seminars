import re
import json
import logging
import requests

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("recipe_assistant")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

mcp = FastMCP(
    name="Помощник по рецептам",
    system_prompt="""
Ты — помощник по кухне. Твоя задача — находить рецепты для пользователей.
Ты можешь искать рецепты по названию блюда или по основному ингредиенту.
Помни: перед тем, как обратиться к поисковому инструменту, тебе нужно перевести блюдо или ингредиент на английский язык.

Используй инструменты:
- search_recipe_by_name: для поиска конкретного блюда (например, "Борщ").
- search_recipe_by_ingredient: для поиска блюд с определенным ингредиентом (например, "курица").

Примеры запросов пользователей:
- "Найди рецепт блинов"
- "Что можно приготовить из говядины?"
- "Покажи, как готовить пасту Карбонара"
"""
)


@mcp.tool()
def search_recipe_by_name(context: Context, 
                          name: str) -> str:
    """
    Ищет рецепт по названию блюда.
    """
    api_url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={name}"

    try:
        response = requests.get(api_url)

        return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        context.logger.error(f"Сетевая ошибка: {e}")

        return json.dumps({"meals": None, "error": "Ошибка сети"})

@mcp.tool()
def search_recipe_by_ingredient(context: Context, 
                                ingredient: str) -> str:
    """
    Ищет рецепты по основному ингредиенту.
    """
    api_url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}"

    try:
        response = requests.get(api_url)

        return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        context.logger.error(f"Сетевая ошибка: {e}")

        return json.dumps({"meals": None, "error": "Ошибка сети"})


@mcp.prompt()
def handle_recipe_query(prompt: str, 
                        context: Context) -> List[Dict[str, Any]]:
    """
    Обработчик запросов о рецептах.
    """
    prompt_lower = prompt.lower()
    match_ingredient = re.search(r"из\s+([а-яё]+)", prompt_lower)
    
    if match_ingredient:
        ingredient = match_ingredient.group(1)
        result_json = search_recipe_by_ingredient(context, ingredient)
        data = json.loads(result_json)
        
        if not data or not data.get("meals"):
            return [
                {
                    "role": "assistant", 
                    "content": f"К сожалению, я не нашел рецептов из продукта '{ingredient}'."
                }
            ]

        response = f"**Вот несколько идей блюд из продукта '{ingredient}':**\n\n"

        for meal in data["meals"][:5]:
            response += f"- {meal['strMeal']}\n"

        response += "\nЧтобы узнать рецепт, спросите меня по названию, например: 'рецепт {название блюда}'."

    else:
        match_name = re.search(r"рецепт\s+([а-яё\s]+)|готовить\s+([а-яё\s]+)", prompt_lower)

        if not match_name:
            return [
                {
                    "role": "assistant", 
                    "content": "Пожалуйста, уточните, ищете ли вы рецепт по названию или из какого-то ингредиента?"
                }
            ]
            
        name = match_name.group(1) or match_name.group(2)
        name = name.strip()
        
        result_json = search_recipe_by_name(context, name)
        data = json.loads(result_json)

        if not data or not data.get("meals"):
            return [
                {
                    "role": "assistant", 
                    "content": f"К сожалению, я не нашел рецепт блюда '{name}'."
                }
            ]
        
        meal = data["meals"][0]
        response = f"###  рецепт: {meal['strMeal']} ({meal.get('strArea', '')})\n\n"
        response += f"![Фото блюда]({meal['strMealThumb']})\n\n"
        response += "**Ингредиенты:**\n"

        for i in range(1, 21):
            ing = meal.get(f'strIngredient{i}')
            measure = meal.get(f'strMeasure{i}')
            
            if ing and ing.strip():
                response += f"- {ing} — {measure}\n"
            else:
                break
        
        response += "\n**Инструкция:**\n"
        instructions = meal['strInstructions'].replace('\r\n', '\n').split('\n')

        for step in instructions:
            if step.strip():
                response += f"1. {step.strip()}\n"

    return [
        {
            "role": "assistant", 
            "content": response
        }
    ]

if __name__ == "__main__":
    mcp.run(transport="stdio")