# TensorRT-LLM + Triton Server Setup Guide

Это руководство содержит пошаговую инструкцию по настройке и запуску TensorRT-LLM с Triton Inference Server для высокопроизводительного инференса языковых моделей.

## 🚀 Быстрый старт

### 1. Запуск Docker контейнера

```bash
docker run --gpus all -it --ipc=host --ulimit memlock=-1 --ulimit stack=67108864 \
  --name tensorrt_llama -p 8000:8000 -p 8001:8001 -p 8002:8002 \
  --volume C:\Users\tryma\triton_project:/workspace \
  --volume C:\Users\tryma\triton_project\hf_cache:/root/.cache/huggingface \
  --volume C:\Users\tryma\TensorRT-LLM:/workspace/TensorRT-LLM \
  --workdir /workspace nvcr.io/nvidia/tritonserver:25.06-trtllm-python-py3 /bin/bash
```

### 2. Конвертация модели

```bash
# Создайте директорию для чекпоинта
mkdir -p /workspace/model_checkpoint

# Конвертируйте вашу модель llama3_2_1b_local
python3 /app/examples/models/core/llama/convert_checkpoint.py \
  --model_dir /workspace/local_models/llama3_2_1b_local \
  --output_dir /workspace/model_checkpoint \
  --dtype float16
```

### 3. Сборка TensorRT движка

```bash
# Создайте директорию для движка
mkdir -p /workspace/trt_engines

# Соберите TensorRT движок
trtllm-build --checkpoint_dir /workspace/model_checkpoint \
  --output_dir /workspace/trt_engines \
  --gemm_plugin float16 \
  --gpt_attention_plugin float16 \
  --remove_input_padding enable \
  --context_fmha enable \
  --paged_kv_cache enable \
  --max_batch_size 8 \
  --max_input_len 2048 \
  --max_seq_len 2560 \
  --max_num_tokens 4096
```

### 4. Настройка Triton Server

```bash
# Создайте директорию для репозитория моделей
mkdir -p /workspace/model_repo

# Скопируйте шаблоны конфигурации
cp -r /app/all_models/inflight_batcher_llm/* /workspace/model_repo/

# Установите переменные окружения
export TOKENIZER_DIR="/workspace/local_models/llama3_2_1b_local" \
ENGINE_DIR="/workspace/trt_engines" \
MAX_BATCH_SIZE=8 \
INSTANCE_COUNT=1 \
DECOUPLED_MODE=false \
TRITON_BACKEND="tensorrtllm" \
LOGITS_DATATYPE="TYPE_FP32" \
MAX_QUEUE_DELAY_MS=0 \
MAX_QUEUE_SIZE=0 \
ADD_SPECIAL_TOKENS=True \
MAX_NUM_IMAGES=1 \
SKIP_SPECIAL_TOKENS=True \
MAX_BEAM_WIDTH=1 \
MAX_TOKENS_IN_PAGED_KV_CACHE=2560 \
MAX_ATTENTION_WINDOW_SIZE=2560 \
KV_CACHE_FREE_GPU_MEM_FRACTION=0.5 \
EXCLUDE_INPUT_IN_OUTPUT=True \
ENABLE_KV_CACHE_REUSE=False \
BATCHING_STRATEGY="inflight_fused_batching" \
MAX_QUEUE_DELAY_MICROSECONDS=0 \
GPU_DEVICE_IDS=0 \
ENCODER_INPUT_FEATURES_DATA_TYPE="TYPE_FP16"
```

### 5. Настройка конфигураций

```bash
# Настройка препроцессинга
python3 /app/tools/fill_template.py -i /workspace/model_repo/preprocessing/config.pbtxt \
  tokenizer_dir:${TOKENIZER_DIR},triton_max_batch_size:${MAX_BATCH_SIZE},preprocessing_instance_count:${INSTANCE_COUNT},max_queue_delay_microseconds:${MAX_QUEUE_DELAY_MICROSECONDS},max_queue_size:${MAX_QUEUE_SIZE},add_special_tokens:${ADD_SPECIAL_TOKENS},engine_dir:${ENGINE_DIR},max_num_images:${MAX_NUM_IMAGES}

# Настройка постпроцессинга
python3 /app/tools/fill_template.py -i /workspace/model_repo/postprocessing/config.pbtxt \
  tokenizer_dir:${TOKENIZER_DIR},triton_max_batch_size:${MAX_BATCH_SIZE},postprocessing_instance_count:${INSTANCE_COUNT},skip_special_tokens:${SKIP_SPECIAL_TOKENS}

# Настройка BLS (Business Logic Scripting)
python3 /app/tools/fill_template.py -i /workspace/model_repo/tensorrt_llm_bls/config.pbtxt \
  triton_max_batch_size:${MAX_BATCH_SIZE},decoupled_mode:${DECOUPLED_MODE},bls_instance_count:${INSTANCE_COUNT},logits_datatype:${LOGITS_DATATYPE}

# Настройка ансамбля моделей
python3 /app/tools/fill_template.py -i /workspace/model_repo/ensemble/config.pbtxt \
  triton_max_batch_size:${MAX_BATCH_SIZE},logits_datatype:${LOGITS_DATATYPE}

# Настройка основной конфигурации модели TensorRT-LLM
python3 /app/tools/fill_template.py -i /workspace/model_repo/tensorrt_llm/config.pbtxt \
  triton_backend:${TRITON_BACKEND},triton_max_batch_size:${MAX_BATCH_SIZE},decoupled_mode:${DECOUPLED_MODE},engine_dir:${ENGINE_DIR},batching_strategy:${BATCHING_STRATEGY},logits_datatype:${LOGITS_DATATYPE},max_beam_width:${MAX_BEAM_WIDTH},max_tokens_in_paged_kv_cache:${MAX_TOKENS_IN_PAGED_KV_CACHE},max_attention_window_size:${MAX_ATTENTION_WINDOW_SIZE},kv_cache_free_gpu_mem_fraction:${KV_CACHE_FREE_GPU_MEM_FRACTION},exclude_input_in_output:${EXCLUDE_INPUT_IN_OUTPUT},enable_kv_cache_reuse:${ENABLE_KV_CACHE_REUSE},max_queue_delay_microseconds:${MAX_QUEUE_DELAY_MICROSECONDS},encoder_input_features_data_type:${ENCODER_INPUT_FEATURES_DATA_TYPE},gpu_device_ids:${GPU_DEVICE_IDS}
```

### 6. Запуск Triton Server

```bash
python3 /app/scripts/launch_triton_server.py --world_size=1 --model_repo=/workspace/model_repo
```

## 📚 Подробное объяснение команд и параметров

### Команда `trtllm-build`

Команда `trtllm-build` компилирует языковую модель в высокопроизводительный движок TensorRT-LLM:

```bash
trtllm-build --checkpoint_dir /workspace/model_checkpoint \
             --output_dir /workspace/trt_engines \
             --gemm_plugin float16 \
             --gpt_attention_plugin float16 \
             --remove_input_padding enable \
             --context_fmha enable \
             --paged_kv_cache enable \
             --max_batch_size 8 \
             --max_input_len 2048 \
             --max_seq_len 2560 \
             --max_num_tokens 4096
```

#### Пути к файлам
- `--checkpoint_dir /workspace/model_checkpoint` - путь к директории с весами исходной модели
- `--output_dir /workspace/trt_engines` - путь для сохранения скомпилированного движка

#### Плагины и точность вычислений
- `--gemm_plugin float16` - использует точность float16 для матричных вычислений
- `--gpt_attention_plugin float16` - использует точность float16 для механизма внимания

#### Оптимизации производительности
- `--remove_input_padding enable` - исключает обработку паддинг-токенов
- `--context_fmha enable` - включает Fused Multi-Head Attention для контекста
- `--paged_kv_cache enable` - активирует интеллектуальное управление памятью K/V кэша

#### Ограничения размеров
- `--max_batch_size 8` - максимальное количество одновременных запросов
- `--max_input_len 2048` - максимальная длина входного промпта
- `--max_seq_len 2560` - максимальная общая длина последовательности
- `--max_num_tokens 4096` - общий пул токенов для K/V кэша

### Переменные окружения Triton Server

#### Основные пути и идентификаторы
- `TOKENIZER_DIR` - путь к файлам токенизатора
- `ENGINE_DIR` - путь к скомпилированному движку TensorRT-LLM
- `TRITON_BACKEND` - бэкенд для выполнения модели (tensorrtllm)
- `GPU_DEVICE_IDS` - ID GPU для использования

#### Производительность и обработка запросов
- `INSTANCE_COUNT` - количество экземпляров модели на GPU
- `MAX_BATCH_SIZE` - максимальное количество запросов в батче
- `BATCHING_STRATEGY` - стратегия батчинга (inflight_fused_batching)
- `MAX_QUEUE_DELAY_MICROSECONDS` - время ожидания для формирования батча

#### Управление памятью GPU
- `MAX_TOKENS_IN_PAGED_KV_CACHE` - максимальное количество токенов в K/V кэше
- `MAX_ATTENTION_WINDOW_SIZE` - размер окна внимания
- `KV_CACHE_FREE_GPU_MEM_FRACTION` - доля свободной памяти для K/V кэша

#### Конфигурация генерации
- `DECOUPLED_MODE` - режим ответа сервера (false для полного ответа)
- `LOGITS_DATATYPE` - тип данных для логитов
- `ADD_SPECIAL_TOKENS` - автоматическое добавление специальных токенов
- `SKIP_SPECIAL_TOKENS` - пропуск специальных токенов в ответе
- `MAX_BEAM_WIDTH` - ширина луча для Beam Search
- `EXCLUDE_INPUT_IN_OUTPUT` - исключение входного промпта из ответа
- `ENABLE_KV_CACHE_REUSE` - повторное использование K/V кэша

## 🔧 Настройка под ваши нужды

### Изменение размера модели
Для работы с моделями разного размера измените:
- `MAX_BATCH_SIZE` - в зависимости от доступной VRAM
- `MAX_INPUT_LEN` и `MAX_SEQ_LEN` - под ваши задачи
- `KV_CACHE_FREE_GPU_MEM_FRACTION` - для оптимизации использования памяти

### Оптимизация производительности
- Увеличьте `INSTANCE_COUNT` для лучшей пропускной способности
- Настройте `MAX_QUEUE_DELAY_MICROSECONDS` для баланса latency/throughput
- Используйте `ENABLE_KV_CACHE_REUSE=True` для многоходовых диалогов

## 🚨 Важные замечания

1. Убедитесь, что у вас достаточно VRAM для выбранных параметров
2. Значения `MAX_BATCH_SIZE` должны совпадать в команде сборки и настройке Triton
3. Пути к моделям должны быть корректными для вашей системы
4. Для продакшена рекомендуется настроить мониторинг и логирование

## 📖 Дополнительные ресурсы

- [TensorRT-LLM Documentation](https://github.com/NVIDIA/TensorRT-LLM)
- [Triton Inference Server](https://github.com/triton-inference-server/server)
- [NVIDIA NGC Containers](https://catalog.ngc.nvidia.com/) 