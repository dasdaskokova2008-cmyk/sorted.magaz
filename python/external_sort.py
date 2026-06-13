"""
Внешняя сортировка CSV-файла магазина.
Память: не больше 10% от размера исходного файла.
Формат: product_id, product_name, price, quantity, expiry_date
"""

import csv
import heapq
import os
import shutil
import time
from typing import Callable, List, Tuple
from datetime import datetime

# какое поле по чему сортируем (индексы для 5 колонок)
SORT_KEYS = {
    "product_id": lambda row: int(row[0]),       # колонка 0
    "product_name": lambda row: row[1],           # колонка 1
    "price": lambda row: float(row[2]),           # колонка 2
    "quantity": lambda row: int(row[3]),          # колонка 3
    "expiry_date": lambda row: datetime.strptime(row[4], "%Y-%m-%d"),  # колонка 4
}


def _memory_limit_bytes(input_path: str) -> int:
    file_size = os.path.getsize(input_path)
    return max(file_size // 10, 5 * 1024 * 1024)  # минимум 5 МБ


def _estimate_row_bytes(sample_line: str) -> int:
    return max(len(sample_line.encode("utf-8")), 20)


def _split_and_sort(
    input_path: str,
    temp_dir: str,
    key_func: Callable,
) -> Tuple[List[str], float]:
    """Читаем кусками, сортируем в памяти, пишем временные файлы."""
    mem_limit = _memory_limit_bytes(input_path)
    chunk_files: List[str] = []
    chunk_id = 0
    start = time.time()

    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        batch: List[list] = []
        used_bytes = 0
        row_bytes = 30

        for row in reader:
            if len(row) < 5:  # теперь 5 колонок
                continue
            if not batch:
                row_bytes = _estimate_row_bytes(",".join(row))

            batch.append(row)
            used_bytes += row_bytes

            if used_bytes >= mem_limit:
                batch.sort(key=key_func)
                chunk_path = os.path.join(temp_dir, f"chunk_{chunk_id:04d}.tmp")
                with open(chunk_path, "w", encoding="utf-8", newline="") as out:
                    writer = csv.writer(out)
                    for r in batch:
                        writer.writerow(r)
                chunk_files.append(chunk_path)
                chunk_id += 1
                batch = []
                used_bytes = 0

        if batch:
            batch.sort(key=key_func)
            chunk_path = os.path.join(temp_dir, f"chunk_{chunk_id:04d}.tmp")
            with open(chunk_path, "w", encoding="utf-8", newline="") as out:
                writer = csv.writer(out)
                for r in batch:
                    writer.writerow(r)
            chunk_files.append(chunk_path)

    split_time = time.time() - start
    return header, chunk_files, split_time


def _merge_chunks(
    header: str,
    chunk_files: List[str],
    output_path: str,
    key_func: Callable,
) -> float:
    """Сливаем отсортированные куски в один файл."""
    start = time.time()
    files = []
    readers = []

    try:
        for path in chunk_files:
            fh = open(path, "r", encoding="utf-8", newline="")
            files.append(fh)
            reader = csv.reader(fh)
            readers.append(reader)

        heap: List[Tuple] = []
        for i, reader in enumerate(readers):
            try:
                row = next(reader)
                heapq.heappush(heap, (key_func(row), i, row))
            except StopIteration:
                pass

        with open(output_path, "w", encoding="utf-8", newline="") as out:
            out.write(f"# {','.join(header)}\n")
            writer = csv.writer(out)
            while heap:
                _, idx, row = heapq.heappop(heap)
                writer.writerow(row)
                try:
                    nxt = next(readers[idx])
                    heapq.heappush(heap, (key_func(nxt), idx, nxt))
                except StopIteration:
                    pass
    finally:
        for fh in files:
            fh.close()

    return time.time() - start


def external_sort(
    input_path: str,
    output_path: str,
    sort_key: str = "product_id",
) -> dict:
    """
    Сортирует input_path -> output_path.
    Возвращает словарь с временем этапов.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(
            f"Файл не найден: {input_path}. Сначала нажми 'Сгенерировать' или выбери другой CSV."
        )

    if sort_key not in SORT_KEYS:
        raise ValueError(f"Ключ должен быть один из: {list(SORT_KEYS.keys())}")

    key_func = SORT_KEYS[sort_key]
    temp_dir = output_path + "_tmp_chunks"
    os.makedirs(temp_dir, exist_ok=True)

    total_start = time.time()
    chunk_count = 0
    split_time = 0.0
    merge_time = 0.0

    try:
        header, chunk_files, split_time = _split_and_sort(input_path, temp_dir, key_func)
        chunk_count = len(chunk_files)
        merge_time = _merge_chunks(header, chunk_files, output_path, key_func)
    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    total_time = time.time() - total_start

    return {
        "split_seconds": round(split_time, 2),
        "merge_seconds": round(merge_time, 2),
        "total_seconds": round(total_time, 2),
        "sort_key": sort_key,
        "chunks": chunk_count,
    }


def check_sorted(output_path: str, sort_key: str, sample: int = 100) -> Tuple[bool, str]:
    """Проверяем что файл отсортирован (читаем sample строк)."""
    if sort_key not in SORT_KEYS:
        return False, "Неизвестный ключ"

    key_func = SORT_KEYS[sort_key]
    prev = None
    count = 0

    with open(output_path, "r", encoding="utf-8", newline="") as f:
        for line in f:
            if line.startswith("#"):
                continue
            row = line.strip().split(",")
            if len(row) < 5:  # теперь 5 колонок
                continue
            val = key_func(row)
            if prev is not None and val < prev:
                return False, f"Ошибка на строке {count}: {val} < {prev}"
            prev = val
            count += 1
            if count >= sample:
                break

    return True, f"Первые {count} строк отсортированы по {sort_key}"


def read_preview(file_path: str, lines: int = 10, from_end: bool = False) -> str:
    """Показать начало или конец файла."""
    if not os.path.isfile(file_path):
        return "Файл не найден"

    if not from_end:
        result = []
        with open(file_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= lines:
                    break
                result.append(line.rstrip())
        return "\n".join(result)

    # конец файла — читаем блок с хвоста
    block = 64 * 1024
    with open(file_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - block))
        text = f.read().decode("utf-8", errors="ignore")
    all_lines = text.splitlines()
    return "\n".join(all_lines[-lines:])