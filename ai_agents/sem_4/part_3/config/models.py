"""Pydantic data models for AutoGen Multi-Agent System."""

from typing import List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError as e:
    raise ImportError(f"Pydantic не установлен. Установите: pip install pydantic pydantic-settings. Ошибка: {e}")


class Plan(BaseModel):
    """Модель для плана реализации от Архитектора."""
    plan: List[str] = Field(..., description="Пошаговый план реализации.")
    data_query: Optional[str] = Field(None, description="Точный запрос для веб-поиска, если нужен.")
    dependencies: List[str] = Field(default_factory=list, description="Необходимые Python-библиотеки.")


class ExtractedData(BaseModel):
    """Модель для извлеченных данных от DataExtractor."""
    price: Optional[float] = Field(None, description="Извлеченная цена. null, если не найдена.")


class GeneratedCode(BaseModel):
    """Модель для сгенерированного кода от Программиста."""
    description: str = Field(..., description="Краткое описание того, что делает скрипт.")
    code: str = Field(..., description="Полный код скрипта.")


class CodeReview(BaseModel):
    """Модель для результатов code review от Ревьюера."""
    review_comments: List[str] = Field(..., description="Список комментариев по коду.")
    test_code: str = Field(..., description="Код тестов для скрипта.")
    improvements: List[str] = Field(default_factory=list, description="Предложения по улучшению.")


class Documentation(BaseModel):
    """Модель для документации от ТехПисателя."""
    title: str = Field(..., description="Заголовок документации.")
    description: str = Field(..., description="Описание проекта.")
    usage_examples: List[str] = Field(..., description="Примеры использования.")
    api_documentation: str = Field(..., description="Документация API/функций.")


class ProblemSolution(BaseModel):
    """Модель для решения проблем от TeamLead."""
    problem_analysis: str = Field(..., description="Анализ проблемы.")
    target_agent: str = Field(..., description="Кого исправлять: 'Программист' или 'Ревьюер'.")
    specific_instructions: str = Field(..., description="Конкретные инструкции для исправления.")
    expected_outcome: str = Field(..., description="Ожидаемый результат после исправления.") 