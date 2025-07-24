"""Raw AutoGen conversation logger for debugging and analysis."""

import os
import logging
from datetime import datetime


class AutoGenRawLogger:
    """Система Raw Логирования AutoGen для отладки и анализа."""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.raw_log_file = os.path.join(workspace_dir, "autogen_raw_output.log")
        self.session_start_time = datetime.now()
        
        # Создаем отдельный логгер для raw AutoGen output
        self.raw_logger = logging.getLogger("autogen_raw")
        self.raw_logger.setLevel(logging.DEBUG)
        
        # Убираем все существующие handlers для чистого вывода
        self.raw_logger.handlers.clear()
        self.raw_logger.propagate = False
        
        # Создаем file handler для raw логов
        self.file_handler = logging.FileHandler(self.raw_log_file, mode='w', encoding='utf-8')
        self.file_handler.setLevel(logging.DEBUG)
        
        # Простой формат для raw логов - время + сообщение
        formatter = logging.Formatter('%(asctime)s | %(message)s')
        self.file_handler.setFormatter(formatter)
        
        self.raw_logger.addHandler(self.file_handler)
        
        # Инициализация raw лог-файла
        self._initialize_raw_log()
        
        # Настраиваем перехват AutoGen логов
        self._setup_autogen_logging()
    
    def _initialize_raw_log(self):
        """Создает заголовок raw лог-файла."""
        header = f"""
================================================================================
                    AUTOGEN MULTI-AGENT SYSTEM - RAW OUTPUT LOG                    
================================================================================
Session started: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}
Workspace: {self.workspace_dir}
================================================================================

"""
        self.raw_logger.info(header.strip())
    
    def _setup_autogen_logging(self):
        """Настраивает перехват логов от AutoGen."""
        # Получаем корневой логгер AutoGen
        autogen_logger = logging.getLogger("autogen")
        
        # Создаем custom handler для перехвата AutoGen логов
        class AutoGenRawHandler(logging.Handler):
            def __init__(self, raw_logger):
                super().__init__()
                self.raw_logger = raw_logger
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.raw_logger.info(f"[AUTOGEN-{record.levelname}] {msg}")
                except Exception:
                    pass
        
        # Добавляем наш handler к AutoGen логгеру
        raw_handler = AutoGenRawHandler(self.raw_logger)
        raw_handler.setFormatter(logging.Formatter('%(message)s'))
        autogen_logger.addHandler(raw_handler)
        autogen_logger.setLevel(logging.DEBUG)
    
    def log_chat_initiation(self, initiator: str, recipient: str, message: str):
        """Логирует начало чата между агентами."""
        log_entry = f"""
{'='*80}
CHAT INITIATION: {initiator} → {recipient}
{'='*80}
Initial Message:
{message}
{'='*80}
"""
        self.raw_logger.info(log_entry.strip())
    
    def log_agent_response(self, agent_name: str, response: str):
        """Логирует ответ агента."""
        log_entry = f"""
{'─'*80}
AGENT RESPONSE: {agent_name}
{'─'*80}
{response}
{'─'*80}
"""
        self.raw_logger.info(log_entry.strip())
    
    def log_tool_call(self, agent_name: str, tool_name: str, tool_input: str, tool_output: str):
        """Логирует вызов инструмента."""
        log_entry = f"""
{'+'*80}
TOOL CALL: {agent_name} → {tool_name}
{'+'*80}
INPUT:
{tool_input}
{'─'*40}
OUTPUT:
{tool_output}
{'+'*80}
"""
        self.raw_logger.info(log_entry.strip())
    
    def log_chat_history(self, chat_history: list, context: str = ""):
        """Логирует полную историю чата."""
        log_entry = f"""
{'*'*80}
CHAT HISTORY {f'({context})' if context else ''}
{'*'*80}
"""
        self.raw_logger.info(log_entry.strip())
        
        for i, msg in enumerate(chat_history):
            role = msg.get('role', msg.get('name', 'unknown'))
            content = msg.get('content', '')
            
            entry = f"""
[{i+1}] {role.upper()}:
{'-' * (len(role) + 10)}
{content}
"""
            self.raw_logger.info(entry.strip())
        
        self.raw_logger.info('*' * 80)
    
    def log_session_end(self):
        """Логирует завершение сессии."""
        end_time = datetime.now()
        duration = end_time - self.session_start_time
        
        footer = f"""

================================================================================
                              SESSION COMPLETED                              
================================================================================
End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
Duration: {str(duration).split('.')[0]}
================================================================================
"""
        self.raw_logger.info(footer.strip())
        
        # Закрываем file handler
        if self.file_handler:
            self.file_handler.close()
            self.raw_logger.removeHandler(self.file_handler) 