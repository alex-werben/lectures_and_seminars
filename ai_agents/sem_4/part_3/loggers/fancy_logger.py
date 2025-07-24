"""Fancy visual logger with beautiful formatting and emoji indicators."""

import os
import re
import logging
from datetime import datetime


class FancyLogger:
    """Система Fancy Логирования с красивым визуальным форматированием."""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.log_file = os.path.join(workspace_dir, "agents_workflow.log")
        self.session_start_time = datetime.now()
        
        # Эмодзи для каждого агента
        self.agent_emojis = {
            "Архитектор": "🏗️",
            "DataExtractor": "🔍", 
            "Программист": "💻",
            "Ревьюер": "🧪",
            "ТехПисатель": "📝",
            "TeamLead": "👨‍💼",
            "Оркестратор": "🎭"
        }
        
        # Инициализация лог-файла
        self._initialize_log()
    
    def _initialize_log(self):
        """Создает красивый заголовок лог-файла."""
        header = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🤖 AUTOGEN AGENTS WORKFLOW LOG                      ║
║                                                                              ║
║  Сессия начата: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}                                           ║
║  Рабочая директория: {self.workspace_dir:<48} ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(header)
    
    def log_agent_action(self, agent_name: str, action: str, details: str = ""):
        """Логирует действие агента с красивым форматированием."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        emoji = self.agent_emojis.get(agent_name, "🤖")
        
        # Формируем красивую запись
        log_entry = f"""
┌─ {timestamp} ─────────────────────────────────────────────────────────────────┐
│ {emoji} АГЕНТ: {agent_name:<20} │ ДЕЙСТВИЕ: {action:<30} │
├─────────────────────────────────────────────────────────────────────────────┤
"""
        
        if details:
            # Разбиваем длинный текст на строки
            lines = details.split('\n')
            for line in lines:
                # Обрезаем длинные строки
                if len(line) > 75:
                    line = line[:72] + "..."
                log_entry += f"│ {line:<75} │\n"
        
        log_entry += "└─────────────────────────────────────────────────────────────────────────────┘\n"
        
        # Записываем в файл
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Также выводим в консоль (сокращенно)
        console_msg = f"{emoji} {agent_name}: {action}"
        if details and len(details) < 100:
            console_msg += f" | {details}"
        logging.getLogger(__name__).info(console_msg)
    
    def log_phase_start(self, phase_name: str, phase_number: int):
        """Логирует начало новой фазы."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        phase_header = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ {timestamp} │ 🚀 ФАЗА {phase_number}: {phase_name:<50} ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(phase_header)
        
        logging.getLogger(__name__).info(f"🚀 ФАЗА {phase_number}: {phase_name}")
    
    def log_error(self, agent_name: str, error_msg: str):
        """Логирует ошибку с выделением."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        emoji = self.agent_emojis.get(agent_name, "🤖")
        
        error_entry = f"""
┌─ {timestamp} ─ ❌ ОШИБКА ─────────────────────────────────────────────────────┐
│ {emoji} АГЕНТ: {agent_name:<67} │
├─────────────────────────────────────────────────────────────────────────────┤
"""
        
        # Разбиваем сообщение об ошибке
        lines = error_msg.split('\n')
        for line in lines[:5]:  # Ограничиваем количество строк
            if len(line) > 75:
                line = line[:72] + "..."
            error_entry += f"│ ❌ {line:<72} │\n"
        
        error_entry += "└─────────────────────────────────────────────────────────────────────────────┘\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(error_entry)
        
        logging.getLogger(__name__).error(f"❌ {agent_name}: {error_msg[:100]}...")
    
    def log_success(self, message: str):
        """Логирует успешное завершение."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        success_entry = f"""
┌─ {timestamp} ─ ✅ УСПЕХ ──────────────────────────────────────────────────────┐
│ {message:<75} │
└─────────────────────────────────────────────────────────────────────────────┘
"""
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(success_entry)
        
        logging.getLogger(__name__).info(f"✅ {message}")
    
    def log_session_end(self):
        """Логирует завершение сессии."""
        end_time = datetime.now()
        duration = end_time - self.session_start_time
        
        footer = f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                             🏁 СЕССИЯ ЗАВЕРШЕНА                              ║
║                                                                              ║
║  Время завершения: {end_time.strftime('%Y-%m-%d %H:%M:%S')}                                        ║
║  Продолжительность: {str(duration).split('.')[0]:<52} ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(footer)
    
    def log_test_results(self, iteration: int, exit_code: int, test_logs: str, dependencies: list = None):
        """Логирует результаты выполнения тестов."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Определяем статус
        status = "✅ ПРОШЛИ" if exit_code == 0 else "❌ ПРОВАЛИЛИСЬ"
        status_emoji = "✅" if exit_code == 0 else "❌"
        
        # Анализируем логи тестов
        test_stats = self._analyze_test_logs(test_logs)
        
        # Форматируем зависимости
        deps_str = ", ".join(dependencies) if dependencies else "нет"
        if len(deps_str) > 60:
            deps_str = deps_str[:57] + "..."
        
        test_entry = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║ {timestamp} │ 🧪 РЕЗУЛЬТАТЫ ТЕСТОВ │ Итерация {iteration:<3} │ {status:<12} ║
╠─────────────────────────────────────────────────────────────────────────────┤
║ {status_emoji} Код выхода: {exit_code:<3} │ 📦 Зависимости: {deps_str:<35} ║
║ 🎯 Прошло тестов: {test_stats['passed']:<3} │ ❌ Провалилось: {test_stats['failed']:<3} │ ⚠️  Ошибок: {test_stats['errors']:<3} ║
"""
        
        # Добавляем основные ошибки (первые 3)
        if test_stats['error_details']:
            test_entry += "╠─────────────────────────────────────────────────────────────────────────────┤\n"
            test_entry += "║ 🔍 ОСНОВНЫЕ ОШИБКИ:                                                          ║\n"
            
            for i, error in enumerate(test_stats['error_details'][:3]):
                error_line = error[:69]  # Ограничиваем длину
                if len(error) > 69:
                    error_line += "..."
                test_entry += f"║ {i+1}. {error_line:<72} ║\n"
        
        test_entry += "╚══════════════════════════════════════════════════════════════════════════════╝\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(test_entry)
        
        # Консольный вывод
        console_msg = f"🧪 Тесты итерация {iteration}: {status} (код {exit_code})"
        if test_stats['passed'] > 0 or test_stats['failed'] > 0:
            console_msg += f" | ✅{test_stats['passed']} ❌{test_stats['failed']}"
        logging.getLogger(__name__).info(console_msg)
        
        # Логируем критические ошибки отдельно
        if exit_code != 0 and test_stats['critical_errors']:
            for error in test_stats['critical_errors'][:2]:  # Только первые 2
                logging.getLogger(__name__).error(f"🔥 Критическая ошибка теста: {error}")
    
    def _analyze_test_logs(self, test_logs: str) -> dict:
        """Анализирует логи тестов и извлекает статистику."""
        stats = {
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'error_details': [],
            'critical_errors': []
        }
        
        if not test_logs:
            return stats
        
        lines = test_logs.split('\n')
        
        # Ищем статистику pytest
        for line in lines:
            # Формат: "= 2 failed, 3 passed in 1.23s ="
            if 'failed' in line and 'passed' in line:
                failed_match = re.search(r'(\d+)\s+failed', line)
                passed_match = re.search(r'(\d+)\s+passed', line)
                if failed_match:
                    stats['failed'] = int(failed_match.group(1))
                if passed_match:
                    stats['passed'] = int(passed_match.group(1))
            
            # Ищем только количество прошедших тестов
            elif 'passed' in line and 'failed' not in line:
                passed_match = re.search(r'(\d+)\s+passed', line)
                if passed_match:
                    stats['passed'] = int(passed_match.group(1))
        
        # Извлекаем ошибки
        current_error = ""
        collecting_error = False
        
        for line in lines:
            # Начало ошибки
            if line.startswith('FAILED') or 'AssertionError' in line or 'Error:' in line:
                if current_error:
                    stats['error_details'].append(current_error.strip())
                current_error = line
                collecting_error = True
                
                # Критические ошибки
                if any(keyword in line for keyword in ['ImportError', 'ModuleNotFoundError', 'SyntaxError']):
                    stats['critical_errors'].append(line.strip())
                    stats['errors'] += 1
            
            elif collecting_error and line.strip():
                if line.startswith(' ') or line.startswith('\t'):  # Продолжение ошибки
                    current_error += " " + line.strip()
                else:
                    # Новая секция - завершаем текущую ошибку
                    if current_error:
                        stats['error_details'].append(current_error.strip())
                        current_error = ""
                    collecting_error = False
        
        # Добавляем последнюю ошибку
        if current_error:
            stats['error_details'].append(current_error.strip())
        
        return stats
    
    def log_improvement_cycle(self, iteration: int, max_iterations: int, action: str, details: str = ""):
        """Логирует действия в цикле улучшений."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        cycle_entry = f"""
┌─ {timestamp} ─ 🔄 ЦИКЛ УЛУЧШЕНИЙ ──────────────────────────────────────────────┐
│ 🎯 Итерация: {iteration}/{max_iterations:<3} │ 🔧 Действие: {action:<45} │
"""
        
        if details:
            lines = details.split('\n')
            for line in lines[:2]:  # Максимум 2 строки деталей
                if len(line) > 75:
                    line = line[:72] + "..."
                cycle_entry += f"│ 📋 {line:<74} │\n"
        
        cycle_entry += "└─────────────────────────────────────────────────────────────────────────────┘\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(cycle_entry)
        
        logging.getLogger(__name__).info(f"🔄 Итерация {iteration}/{max_iterations}: {action}")
    
    def log_docker_setup(self, dependencies: list, docker_enabled: bool):
        """Логирует настройку Docker среды."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        docker_status = "🐳 ВКЛЮЧЕН" if docker_enabled else "📁 ЛОКАЛЬНО"
        deps_count = len(dependencies)
        deps_preview = ", ".join(dependencies[:3])
        if len(dependencies) > 3:
            deps_preview += f" и еще {len(dependencies) - 3}"
        
        docker_entry = f"""
┌─ {timestamp} ─ 🐳 НАСТРОЙКА СРЕДЫ ТЕСТИРОВАНИЯ ──────────────────────────────┐
│ 🎯 Режим: {docker_status:<12} │ 📦 Зависимостей: {deps_count:<3} │ 🔧 Установка...    │
│ 📋 Пакеты: {deps_preview:<63} │
└─────────────────────────────────────────────────────────────────────────────┘
"""
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(docker_entry)
        
        logging.getLogger(__name__).info(f"🐳 Docker тестирование: {docker_status} | Зависимости: {deps_count}") 