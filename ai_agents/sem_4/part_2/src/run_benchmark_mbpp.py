#!/usr/bin/env python
"""Оценка модели Ollama на наборе задач MBPP.

Запуск:
    python test_bench.py --model qwen2.5-coder:14b --limit 10

Если параметры не указаны, используются значения по-умолчанию.
"""

import argparse
import sys
import textwrap
import re
from pathlib import Path

import ollama
from datasets import load_dataset

# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def load_mbpp_dataset(split: str = "test"):
    """Загружает *sanitized* версию датасета MBPP с HuggingFace."""
    try:
        return load_dataset("mbpp", "sanitized")[split]
    except Exception as e:
        print(f"Ошибка при загрузке датасета: {e}")
        sys.exit(1)


def extract_code_from_response(response_text: str) -> str:
    """Извлекает Python-код из ответа модели.

    Сначала пытается найти блоки ```python ...```. Если их нет, 
    считается, что весь ответ является кодом.
    """
    code_block_match = re.search(r"```(?:python\n)?(.*?)```", response_text, re.DOTALL)
    if code_block_match:
        return textwrap.dedent(code_block_match.group(1)).strip()
    return textwrap.dedent(response_text).strip()


def build_prompt(docstring: str, function_signature: str) -> str:
    """Формирует prompt, отправляемый модели (на английском для лучшего качества)."""
    return (
        "You are an expert Python programmer. Complete the following Python "
        "function **body** based on the docstring.\n"
        "Return *only* valid Python code. Do NOT add explanations, comments, or "
        "markdown fences.\n\n"
        f'"""\n{docstring}\n"""\n'
        f"{function_signature}\n"
    )


def evaluate_problem(
    ollama_client: "ollama.Client",
    model: str,
    example: dict,
    verbose: bool = False,
) -> bool:
    """Проверяет одну задачу MBPP. Возвращает True, если все тесты прошли.

    При *verbose* собираются подробные данные (prompt, ответ модели и т.д.), 
    которые выводятся только в случае ошибки.
    """
    prompt = example["prompt"]
    tests = example["test_list"]
    ground_truth_code = example["code"]

    # Extract the first line that starts with 'def' as the signature (skip imports etc.)
    function_signature = next(
        (ln for ln in ground_truth_code.splitlines() if ln.lstrip().startswith("def ")),
        None,
    )
    if function_signature is None:
        raise ValueError("Could not find function signature in ground-truth code")

    full_prompt = build_prompt(prompt, function_signature)

    response = ollama_client.generate(model=model, prompt=full_prompt)
    generated_code_raw = response["response"]
    generated_code = extract_code_from_response(generated_code_raw)

    # Helper to get function name
    def _func_name(line: str) -> str:
        return line.split("(")[0].replace("def", "").strip()

    def _indent_body(lines_list):
        # Dedent relative indentation then indent by 4 spaces
        dedented = textwrap.dedent("\n".join(lines_list)).splitlines()
        return [("    " + ln if ln.strip() else ln) for ln in dedented]

    gen_starts_with_def = generated_code.lstrip().startswith("def")

    if gen_starts_with_def:
        gen_first_def_line = generated_code.splitlines()[0]
        if _func_name(gen_first_def_line) == _func_name(function_signature):
            # Correct signature produced; use as-is.
            script_to_run = generated_code + "\n\n" + "\n".join(tests)
        else:
            # Model returned an entirely new function — drop its def line and use the body.
            body_lines = generated_code.splitlines()[1:]
            indented_body = "\n".join(_indent_body(body_lines))
            full_function = function_signature + "\n" + indented_body
            script_to_run = full_function + "\n\n" + "\n".join(tests)
    else:
        # Response was just the body.
        lines = generated_code.splitlines()
        # Separate potential global lines (e.g., imports) that come before a def
        global_lines = []
        body_candidate_lines = lines
        for idx, l in enumerate(lines):
            if l.lstrip().startswith("def "):
                # Everything after this (including) is body candidate
                global_lines = lines[:idx]  # could be empty
                body_candidate_lines = lines[idx + 1 :]  # skip the def line itself
                break

        # body_candidate_lines remain as-is; textwrap.dedent later normalises

        indented_body = "\n".join(_indent_body(body_candidate_lines))

        script_parts = []
        if global_lines:
            script_parts.append("\n".join(global_lines))
        script_parts.append(function_signature + "\n" + indented_body)
        script_parts.append("\n".join(tests))
        script_to_run = "\n\n".join(script_parts)

    # Capture debug details; we'll print them only if the test fails and verbose is enabled
    debug_lines = []
    if verbose:
        debug_lines.extend([
            "\n--- Отладочная информация для задачи " + str(example.get("task_id", "?")) + " ---",
            "Prompt:\n" + full_prompt,
            "Raw response:\n" + generated_code_raw,
            "Processed code:\n" + generated_code,
            "Executed script (truncated to 500 chars):\n" + script_to_run[:500],
        ])

    # Execute in an isolated namespace
    try:
        exec(script_to_run, {})  # noqa: S102 — intentional use of exec for evaluation
        success = True
    except Exception as ex:
        success = False
        if verbose:
            debug_lines.append("Ошибка выполнения: " + repr(ex))

    if verbose and not success:
        # Print collected debug info only when the test failed
        print("\n".join(debug_lines))

    return success


# ---------------------------------------------------------------------------
# Главный CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Оценка локальной модели Ollama на наборе MBPP.")
    parser.add_argument(
        "--model",
        default="qwen2.5-coder:14b",
        help="Название модели Ollama (должна быть уже скачана локально)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Сколько задач проверять (по-умолчанию 10, -1 — без ограничений)",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["train", "validation", "test"],
        help="Какую часть датасета MBPP использовать (по-умолчанию test)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Показывать подробные логи (prompt, код и т.п.) при ошибке",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    dataset = load_mbpp_dataset(args.split)
    # Если limit == -1 → проверяем на всех примерах
    if args.limit is not None and args.limit > -1:
        dataset = dataset.select(range(min(args.limit, len(dataset))))

    client = ollama.Client()

    total = len(dataset)
    correct = 0

    for example in dataset:
        success = evaluate_problem(client, args.model, example, verbose=args.verbose)
        task_id = example.get("task_id", "?")
        if success:
            correct += 1  # учитываем успешные решения
            print(f"✅ Задача {task_id}: успешно")
        else:
            print(f"❌ Задача {task_id}: ошибка")

    if total:
        accuracy = 100 * correct / total
        print("\n--- Итоги ---")
        print(f"Всего задач:              {total}")
        print(f"Решено правильно:         {correct}")
        print(f"Точность:                 {accuracy:.2f}%")
    else:
        print("Ни одна задача не была проверена.")


if __name__ == "__main__":
    main()