"""Token usage tracking and cost analysis for AutoGen Multi-Agent System."""

import os
import logging
from datetime import datetime


class TokenTracker:
    """Система отслеживания токенов и стоимости LLM вызовов."""
    
    def __init__(self, workspace_dir: str, input_cost: float, output_cost: float):
        self.workspace_dir = workspace_dir
        self.input_cost = input_cost  # Стоимость за входящий токен в рублях
        self.output_cost = output_cost  # Стоимость за исходящий токен в рублях
        self.session_start_time = datetime.now()
        
        # Трекинг токенов по агентам
        self.agent_tokens = {
            "Архитектор": {"input": 0, "output": 0, "calls": 0},
            "DataExtractor": {"input": 0, "output": 0, "calls": 0},
            "Программист": {"input": 0, "output": 0, "calls": 0},
            "Ревьюер": {"input": 0, "output": 0, "calls": 0},
            "ТехПисатель": {"input": 0, "output": 0, "calls": 0},
            "TeamLead": {"input": 0, "output": 0, "calls": 0},
            "Оркестратор": {"input": 0, "output": 0, "calls": 0}
        }
        
        # Файл для логирования токенов
        self.token_log_file = os.path.join(workspace_dir, "tokens_usage.log")
        self._initialize_token_log()
    
    def _initialize_token_log(self):
        """Создает красивый заголовок файла с токенами."""
        header = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        💰 ОТЧЕТ ПО ИСПОЛЬЗОВАНИЮ ТОКЕНОВ                     ║
║                                                                              ║
║  Сессия начата: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}                                           ║
║  Рабочая директория: {self.workspace_dir:<48} ║
║  Стоимость входящего токена: {self.input_cost:.6f} руб.                                ║
║  Стоимость исходящего токена: {self.output_cost:.6f} руб.                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""
        
        with open(self.token_log_file, "w", encoding="utf-8") as f:
            f.write(header)
    
    def estimate_tokens(self, text: str) -> int:
        """Оценивает количество токенов в тексте (примерная формула)."""
        if not text:
            return 0
        
        # Простая оценка: ~4 символа = 1 токен для большинства языков
        # Для русского текста коэффициент может быть выше
        char_count = len(text)
        word_count = len(text.split())
        
        # Используем более точную формулу для смешанного русско-английского текста
        estimated_tokens = max(char_count // 3.5, word_count * 1.3)
        return int(estimated_tokens)
    
    def track_agent_call(self, agent_name: str, input_text: str, output_text: str, 
                        actual_input_tokens: int = None, actual_output_tokens: int = None):
        """Отслеживает использование токенов для вызова агента."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Используем реальные токены если есть, иначе оцениваем
        input_tokens = actual_input_tokens if actual_input_tokens is not None else self.estimate_tokens(input_text)
        output_tokens = actual_output_tokens if actual_output_tokens is not None else self.estimate_tokens(output_text)
        
        # Обновляем статистику агента
        if agent_name in self.agent_tokens:
            self.agent_tokens[agent_name]["input"] += input_tokens
            self.agent_tokens[agent_name]["output"] += output_tokens
            self.agent_tokens[agent_name]["calls"] += 1
        
        # Рассчитываем стоимость
        input_cost = input_tokens * self.input_cost
        output_cost = output_tokens * self.output_cost
        total_cost = input_cost + output_cost
        
        # Логируем в файл
        log_entry = f"""
┌─ {timestamp} ─ 💰 ТОКЕНЫ ─────────────────────────────────────────────────────────┐
│ 🤖 АГЕНТ: {agent_name:<20} │ 🔢 ВЫЗОВ: {self.agent_tokens[agent_name]['calls']:<10} │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📥 Входящие токены: {input_tokens:<8} │ 💰 Стоимость: {input_cost:<10.6f} руб.        │
│ 📤 Исходящие токены: {output_tokens:<7} │ 💰 Стоимость: {output_cost:<10.6f} руб.        │
│ 💵 ОБЩАЯ стоимость вызова: {total_cost:<14.6f} руб.                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 📊 ВХОДЯЩИЙ ТЕКСТ: {len(input_text):<4} симв. │ 📋 ИСХОДЯЩИЙ ТЕКСТ: {len(output_text):<4} симв.     │
└─────────────────────────────────────────────────────────────────────────────────┘
"""
        
        with open(self.token_log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        logging.getLogger(__name__).info(f"💰 {agent_name}: {input_tokens}→{output_tokens} токенов, {total_cost:.4f} руб.")
    
    def get_agent_summary(self, agent_name: str) -> dict:
        """Возвращает сводку по токенам для агента."""
        if agent_name not in self.agent_tokens:
            return {"input": 0, "output": 0, "calls": 0, "cost": 0.0}
        
        data = self.agent_tokens[agent_name]
        input_cost = data["input"] * self.input_cost
        output_cost = data["output"] * self.output_cost
        total_cost = input_cost + output_cost
        
        return {
            "input": data["input"],
            "output": data["output"],
            "calls": data["calls"],
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def get_total_summary(self) -> dict:
        """Возвращает общую сводку по всем токенам."""
        total_input = sum(data["input"] for data in self.agent_tokens.values())
        total_output = sum(data["output"] for data in self.agent_tokens.values())
        total_calls = sum(data["calls"] for data in self.agent_tokens.values())
        
        total_input_cost = total_input * self.input_cost
        total_output_cost = total_output * self.output_cost
        total_cost = total_input_cost + total_output_cost
        
        return {
            "total_input": total_input,
            "total_output": total_output,
            "total_tokens": total_input + total_output,
            "total_calls": total_calls,
            "total_input_cost": total_input_cost,
            "total_output_cost": total_output_cost,
            "total_cost": total_cost
        }
    
    def log_session_summary(self):
        """Логирует итоговую сводку по сессии."""
        end_time = datetime.now()
        duration = end_time - self.session_start_time
        total_summary = self.get_total_summary()
        
        # Создаем детальную сводку по агентам
        agent_details = ""
        for agent_name, data in self.agent_tokens.items():
            if data["calls"] > 0:
                summary = self.get_agent_summary(agent_name)
                agent_details += f"""║ 🤖 {agent_name:<15} │ Вызовов: {data['calls']:<2} │ Токены: {data['input']:<5}→{data['output']:<5} │ {summary['total_cost']:<8.4f} руб. ║
"""
        
        # Общая сводка
        summary_report = f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                           💰 ИТОГОВАЯ СВОДКА ПО ТОКЕНАМ                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ ⏱️  Время сессии: {str(duration).split('.')[0]:<54} ║
║ 🔢 Всего вызовов LLM: {total_summary['total_calls']:<51} ║
║ 📥 Всего входящих токенов: {total_summary['total_input']:<46} ║
║ 📤 Всего исходящих токенов: {total_summary['total_output']:<45} ║
║ 🎯 ИТОГО токенов: {total_summary['total_tokens']:<53} ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ 💰 Стоимость входящих токенов: {total_summary['total_input_cost']:<8.6f} руб.                  ║
║ 💰 Стоимость исходящих токенов: {total_summary['total_output_cost']:<8.6f} руб.                 ║
║ 💵 ОБЩАЯ СТОИМОСТЬ: {total_summary['total_cost']:<12.6f} руб.                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                              📊 ДЕТАЛИЗАЦИЯ ПО АГЕНТАМ                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
{agent_details}╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        with open(self.token_log_file, "a", encoding="utf-8") as f:
            f.write(summary_report)
        
        logging.getLogger(__name__).info(f"💰 ИТОГО: {total_summary['total_tokens']} токенов, {total_summary['total_cost']:.4f} руб.")
        return total_summary 