import os
import re
import json
import scrapy

from scrapy import signals
from datetime import datetime
from configparser import ConfigParser
from typing import Generator, Optional


class TelegramSpider(scrapy.Spider):
    name = "tg_web"
    
    custom_settings = {
        'DOWNLOAD_HANDLERS': {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 35
    }

    def _load_config(self) -> None:
        """
        Загружает конфигурацию из файла config.cfg.
        Устанавливает пути к файлам источников и новостей.
        """
        cfg = ConfigParser(allow_no_value=True)
        cfg.read(os.path.join(os.path.dirname(__file__), 'config.cfg'))

        self.sources_path = str(cfg.get('paths', 'sources_path', fallback='/path/to/tg_data/sources.json'))
        self.news_path = str(cfg.get('paths', 'news_path', fallback='/path/to/tg_data/news.json'))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_config()
        self._load_sources()
        self._load_existed_data()

        self.new_news = []
        self.failed_channels = []

    def _load_sources(self) -> None:
        """
        Загружает источники из JSON-файла.
        """
        try:
            with open(self.sources_path, 'r', encoding='utf-8') as f:
                self.sources = json.load(f)
        except FileNotFoundError:
            self.logger.error("Файл sources.json не найден!")
        except json.JSONDecodeError:
            self.logger.error("Ошибка декодирования sources.json. Проверьте формат файла.")

    def _load_existed_data(self) -> None:
        """
        Загружает существующие новости из JSON-файла.
        """
        try:
            if os.path.exists(self.news_path) and os.path.getsize(self.news_path) > 0:
                with open(self.news_path, 'r', encoding='utf-8') as f:
                    self.existing_news = json.load(f)
                    self.existing_ids = {item['message_id'] for item in self.existing_news}
                    self.logger.info(f"Загружено {len(self.existing_news)} существующих новостей")
            else:
                self.logger.info(f"Файл {self.news_path} не существует или пуст. Будет создан новый.")
                self.existing_news = []
                self.existing_ids = set()
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка декодирования JSON: {e}. Файл будет перезаписан.")
            self.existing_news = []
            self.existing_ids = set()
        except Exception as e:
            self.logger.error(f"Неизвестная ошибка при загрузке существующих данных: {str(e)}")
            self.existing_news = []
            self.existing_ids = set()
        
    def _extract_username(self, 
                          url: str) -> Optional[str]:
        """
        Извлекает username из URL в различных форматах.
        
        Args:
            (url): URL канала
        Returns:
            (Optional[str]): очищенный username или None при ошибке
        """
        if not url:
            return None
            
        try:
            url = url.strip()
            url = url.split('?')[0]
            
            if url.startswith('https://t.me/'):
                return url.split('/')[-1].replace('@', '')
            if url.startswith('t.me/'):
                return url.split('/')[-1].replace('@', '')
            if url.startswith('@'):
                return url[1:]
                
            match = re.search(r'(?:t\.me/|https?://t\.me/)([^/?]+)', url)

            if match:
                return match.group(1).replace('@', '')
                
            return url.replace('@', '')
        except Exception as e:
            self.logger.error(f"Ошибка обработки URL {url}: {str(e)}")

            return None

    def start_requests(self) -> Generator[scrapy.Request, None, None]:
        """
        Генерирует запросы для каждого канала с обработкой ошибок.

        Returns:
            (Generator[scrapy.Request, None, None]): запрос для каждого канала
        """
        print(self.sources)

        for source in self.sources:
            for channel_name, channel_url in source.items():
                username = self._extract_username(channel_url)
                url = f"https://t.me/s/{username}"
                
                self.logger.debug(f"Запрос для канала: {channel_name} ({url})")
                
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    meta={
                        'playwright': True,
                        'channel_name': channel_name,
                        'channel_username': username,
                    }
                )

    def parse(self, 
              response: scrapy.http.Response) -> None:
        """
        Парсит страницу канала и извлекает сообщения.
        
        Args:
            (response): ответ от сервера tg
        """
        self.logger.debug(f"Парсинг канала: {response.meta['channel_name']}")
        
        for message in response.css('.tgme_widget_message'):
            message_id = message.attrib.get('data-post')
            
            datetime_str = message.css('.time::attr(datetime)').get()
            
            if not datetime_str:
                continue
                
            if not message_id:
                try:
                    timestamp = datetime.fromisoformat(datetime_str).timestamp()
                    message_id = f"{response.meta['channel_username']}_{timestamp}"
                except ValueError:
                    continue
            
            if message_id in self.existing_ids:
                self.logger.debug(f"Пропуск дубликата: {message_id}")
                continue

            text_parts = message.css('.tgme_widget_message_text *::text').getall()
            clean_text = ' '.join(text.strip() for text in text_parts if text.strip())
            
            try:
                news_item = {
                    "channel": response.meta['channel_name'],
                    "username": response.meta['channel_username'],
                    "date": datetime.fromisoformat(datetime_str).timestamp(),
                    "text": clean_text,
                    "views": message.css('.tgme_widget_message_views::text').get(),
                    "message_id": message_id,
                    "link": "t.me/s/" + message_id
                }
            except ValueError as e:
                self.logger.error(f"Ошибка формата даты: {datetime_str} - {e}")
                continue
                
            self.logger.debug(f"Найдена новость: {message_id}")
            self.new_news.append(news_item)
            self.existing_ids.add(message_id)

    @classmethod
    def from_crawler(cls, 
                     crawler, 
                     *args, 
                     **kwargs) -> "TelegramSpider":
        """
        Создает экземпляр паука и регистрирует обработчик закрытия.
        
        Returns:
            ("TelegramSpider"): экземпляр паука
        """
        spider = super(TelegramSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        return spider

    def spider_closed(self, 
                      spider) -> None:
        """
        Обработчик закрытия паука: сохраняет все данные.
        
        Args:
            (spider): экземпляр закрытого паука
        """
        all_news = self.existing_news + self.new_news
        self.logger.info(f"Сохранение {len(all_news)} новостей ({len(self.new_news)} новых)")
        
        with open(self.news_path, 'w', encoding='utf-8') as f:
            json.dump(all_news, f, ensure_ascii=False, indent=2)