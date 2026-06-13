# sorted.magaz
# Лабораторная: внешняя сортировка больших файлов

Предметная область: **магазин**. CSV-файл содержит товары:

```
product_id,product_name,price,quantity,expiry_date
1,Соль,71578.74,3925,2026-06-30
```

- `product_id` — ID товара  
- `product_name` - Название товара
- `price` — цена  
- `quantity` — сколько штук осталось на складе  
- `expiry_date` - срок годности товара

## Структура проекта

```
external-sort/
  python/
    generate_data.py   — генератор data.csv (>1 ГБ)
    external_sort.py   — внешняя сортировка на Python
    gui.py             — графический интерфейс
  cpp/
    external_sort.h/cpp — внешняя сортировка на C++
    bindings.cpp       — обёртка pybind11
  setup.py             — сборка C++ модуля
  CMakeLists.txt
  requirements.txt
```

## Алгоритм (внешняя сортировка)

1. **Разбиение** — читаем файл кусками (не больше 10% от размера файла в RAM), сортируем каждый кусок в памяти, пишем во временные файлы.
2. **Слияние** — k-way merge: берём по одной строке из каждого куска, выбираем минимальную, пишем в `sorted.txt`.
3. **Уборка** — временные файлы удаляются.

Ключ сортировки на выбор: `product_id`, `product_name`, `price`, `quantity`, expiry_date`.

## Установка

```bash
cd external-sort
pip install -r requirements.txt
pip install .
```

Для сборки C++ нужен компилятор (Visual Studio Build Tools на Windows).

## Запуск

### GUI (удобно для отчёта)

```bash
python python/gui.py
```

### Из командной строки

```bash
# 1. Сгенерировать файл ~1.1 ГБ
python python/generate_data.py data.csv 1.1

# 2. Сортировка Python
python -c "from external_sort import external_sort; print(external_sort('data.csv','sorted.txt','price'))"

# 3. Сортировка C++ (через pybind11)
python -c "import external_sort_cpp; print(external_sort_cpp.external_sort('data.csv','sorted_cpp.txt','product_id'))"
```

## Требования задания

| Требование | Как выполнено |
|---|---|
| Файл > 1 ГБ | `generate_data.py`, параметр размера |
| Внешняя сортировка C++ и Python | `cpp/external_sort.cpp`, `python/external_sort.py` |
| Выбор ключа | GUI + параметр `sort_key` |
| Память ≤ 10% файла | `memory_limit = file_size / 10` |
| Удаление temp-файлов | `shutil.rmtree` / `fs::remove_all` |
| Время этапов | возвращается `split_seconds`, `merge_seconds` |
| GUI | `python/gui.py` (tkinter) |
| Интеграция C++ | **pybind11** → модуль `external_sort_cpp` |

## Для быстрого теста (не 1 ГБ)

```bash
python python/generate_data.py test.csv 0.01
```

0.01 ГБ ≈ 10 МБ — проверить за секунды.
