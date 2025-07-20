# Triton Inference Server с vLLM: Полное руководство

Это руководство содержит пошаговую инструкцию по развертыванию Triton Inference Server с бэкендом vLLM для работы с Hugging Face моделями. Включает как работу с удаленными моделями, так и с локально скачанными.

## Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Установка Docker образа](#установка-docker-образа)
3. [Работа с удаленными моделями](#работа-с-удаленными-моделями)
4. [Работа с локальными моделями](#работа-с-локальными-моделями)
5. [Диагностика и отладка](#диагностика-и-отладка)
6. [Отправка запросов](#отправка-запросов)

## Предварительные требования

- Docker Desktop версии 28.1.1 или выше
- NVIDIA GPU с поддержкой CUDA
- Установленные NVIDIA драйверы и Docker с поддержкой GPU
- Токен доступа к Hugging Face (для защищенных моделей)

## Установка Docker образа

Скачайте актуальную версию Triton Server с поддержкой vLLM:

```bash
docker pull nvcr.io/nvidia/tritonserver:25.06-vllm-python-py3
```

## Работа с удаленными моделями

### Настройка токена Hugging Face

1. **Примите условия использования модели** на сайте Hugging Face (например, для Gemma)
2. **Создайте токен доступа** в [Settings -> Access Tokens](https://huggingface.co/settings/tokens)
3. **Установите токен как переменную окружения:**

```powershell
$env:HF_TOKEN="hf_ВАШ_ДЛИННЫЙ_ТОКЕН_ДОСТУПА"
```

### Структура проекта для удаленных моделей

```
triton_project/
└── model_repository/
    └── gemma/
        ├── config.pbtxt
        └── 1/
            └── model.json
```

### Конфигурационные файлы

#### `model_repository/gemma/config.pbtxt`

```pbtxt
name: "gemma"
backend: "vllm"
max_batch_size: 256
model_transaction_policy { decoupled: true }
input [ 
  { name: "text_input", data_type: TYPE_STRING, dims: [ -1 ] },
  { name: "stream", data_type: TYPE_BOOL, dims: [ 1 ], optional: true },
  { name: "sampling_parameters", data_type: TYPE_STRING, dims: [ 1 ], optional: true }
]
output [ 
  { name: "text_output", data_type: TYPE_STRING, dims: [ -1 ] } 
]
```

#### `model_repository/gemma/1/model.json`

```json
{
  "model": "google/gemma-2b-it",
  "tensor_parallel_size": 1,
  "gpu_memory_utilization": 0.90
}
```

### Команда запуска для удаленных моделей

```powershell
docker run --gpus all -d --rm -p 8000:8000 -p 8001:8001 -p 8002:8002 --env HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\model_repository",target="/models" --mount type=volume,source=triton_hf_cache,target="/root/.cache/huggingface" --name triton_vllm_server nvcr.io/nvidia/tritonserver:25.06-vllm-python-py3 tritonserver --model-repository=/models --model-control-mode=explicit --load-model=gemma
```

## Работа с локальными моделями

### Шаг 1: Локальная загрузка модели

1. **Установите библиотеку:**
```bash
pip install huggingface_hub
```

2. **Создайте скрипт загрузки `download_model.py`:**

```python
import os
from huggingface_hub import snapshot_download

# ID модели на Hugging Face
model_id = "google/gemma-3-1b-it"

# Папка для сохранения
local_model_dir = "local_models"
local_model_path = os.path.join(local_model_dir, model_id.replace("/", "_"))

print(f"Загрузка модели '{model_id}' в '{local_model_path}'...")

# Скачиваем файлы модели
snapshot_download(
    repo_id=model_id,
    local_dir=local_model_path,
    local_dir_use_symlinks=False,  # Важно для Docker в Windows
    token=os.environ.get("HF_TOKEN")
)

print("Загрузка завершена.")
```

### Шаг 2: Структура проекта для локальных моделей

```
triton_project/
├── local_models/                  # Папка с скачанными моделями
│   └── google_gemma-3-1b-it/     # Файлы модели
│       ├── config.json
│       └── ...
└── model_repository/              # Конфигурация Triton
    └── gemma_local/               # Имя модели для Triton
        ├── config.pbtxt
        └── 1/
            └── model.json
```

### Шаг 3: Конфигурационные файлы для локальных моделей

#### `model_repository/gemma_local/config.pbtxt`

```pbtxt
name: "gemma_local"
backend: "vllm"
max_batch_size: 0
model_transaction_policy {
  decoupled: true
}
input [
  {
    name: "text_input"
    data_type: TYPE_STRING
    dims: [ -1 ]
  },
  {
    name: "stream"
    data_type: TYPE_BOOL
    dims: [ 1 ]
    optional: true
  },
  {
    name: "sampling_parameters"
    data_type: TYPE_STRING
    dims: [ 1 ]
    optional: true
  }
]
output [
  {
    name: "text_output"
    data_type: TYPE_STRING
    dims: [ -1 ]
  }
]
```

#### `model_repository/gemma_local/1/model.json`

```json
{
  "model": "/local_models/google_gemma-3-1b-it",
  "tensor_parallel_size": 1,
  "gpu_memory_utilization": 0.90
}
```

### Шаг 4: Команда запуска для локальных моделей

**Замените путь на ваш реальный:**

```bash
docker run --gpus all -d --rm -p 8000:8000 -p 8001:8001 -p 8002:8002 --env HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\model_repository",target="/models" --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\local_models",target="/local_models" --mount type=volume,source=triton_hf_cache,target="/root/.cache/huggingface" --name triton_vllm_server nvcr.io/nvidia/tritonserver:25.06-vllm-python-py3 tritonserver --model-repository=/models --model-control-mode=explicit --load-model=gemma_local
```

еще один вариант
```bash
docker run --gpus all -d -p 8000:8000 -p 8001:8001 -p 8002:8002 --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\model_repository",target="/models" --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\local_models",target="/local_models" --mount type=volume,source=triton_hf_cache,target="/root/.cache/huggingface" --name triton_vllm nvcr.io/nvidia/tritonserver:25.06-vllm-python-py3 tritonserver --model-repository=/models --model-control-mode=explicit --load-model=llama3_2_1b_local
```

## Диагностика и отладка

### Проверка монтирования папок

Если Docker выдает ошибку `bind source path does not exist`, выполните тест:

```powershell
docker run --rm --mount type=bind,source="C:\Users\<ваше_имя_пользователя>\triton_project\model_repository",target="/data" ubuntu ls -l /data
```

- **Успех:** Вы увидите содержимое папки - синтаксис правильный
- **Провал:** Сбросьте Docker Desktop до заводских настроек

### Отладка падающего контейнера

1. **Уберите флаг `--rm` из команды запуска**
2. **Найдите остановленный контейнер:**
```powershell
docker ps -a
```
3. **Прочитайте логи:**
```powershell
docker logs triton_vllm_server
```

### Проверка успешного запуска

1. **Проверьте статус контейнера:**
```bash
docker ps
```

2. **Просмотрите логи:**
```bash
docker logs triton_vllm_server
```

Успешная загрузка должна показать:
```
+-----------------+---------+--------+
| Model           | Version | Status |
+-----------------+---------+--------+
| gemma_local     | 1       | READY  |
+-----------------+---------+--------+
```

## Отправка запросов

### Python-скрипт для тестирования

```python
import requests
import json

# Эндпоинт для стриминга
url = "http://localhost:8000/v2/models/gemma_local/generate_stream"

# Параметры генерации
sampling_parameters = {
    "max_tokens": 256,
    "temperature": 0.7
}

# Тело запроса
payload = {
    "text_input": "Расскажи в трех предложениях, почему небо голубое.",
    "stream": True,
    "sampling_parameters": json.dumps(sampling_parameters)
}

print("Отправляем запрос...")
try:
    with requests.post(url, json=payload, stream=True) as response:
        response.raise_for_status()
        print("Ответ модели: ", end="")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    content = decoded_line[len("data: "):]
                    if content == "[DONE]":
                        break
                    text_output = json.loads(content).get("text_output", "")
                    print(text_output, end="", flush=True)
        print("\nГенерация завершена.")
except requests.exceptions.RequestException as e:
    print(f"\nОшибка подключения к серверу: {e}")
```

## Разбор команды Docker

### Управление ресурсами
- `--gpus all`: Доступ ко всем GPU (обязательно для vLLM)
- `-d`: Запуск в фоновом режиме
- `--rm`: Автоматическое удаление контейнера после остановки
- `-p 8000:8000 -p 8001:8001 -p 8002:8002`: Проброс портов (HTTP, gRPC, метрики)

### Настройка среды
- `--env HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN`: Передача токена для доступа к защищенным моделям
- `--mount type=bind,source="...",target="/models"`: Монтирование конфигурации Triton
- `--mount type=bind,source="...",target="/local_models"`: Монтирование локальных моделей (только для локальных моделей)
- `--mount type=volume,source=triton_hf_cache,target="/root/.cache/huggingface"`: Кэш Hugging Face

### Конфигурация Triton
- `--model-repository=/models`: Путь к репозиторию моделей
- `--model-control-mode=explicit`: Режим явного управления моделями
- `--load-model=gemma`: Принудительная загрузка модели при старте

## Частые проблемы и решения

1. **Ошибка `path does not exist`**: Проверьте правильность пути и выполните тест монтирования
2. **Контейнер сразу останавливается**: Уберите `--rm` и проверьте логи
3. **Ошибка `401 Client Error`**: Проверьте токен Hugging Face и принятие условий использования
4. **Модель не загружается**: Проверьте структуру папок и содержимое конфигурационных файлов
5. **Сервер выключается после загрузки**: Используйте флаги `--model-control-mode=explicit` и `--load-model` 