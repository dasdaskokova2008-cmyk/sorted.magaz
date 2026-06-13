"""
Генератор тестовых данных для магазина.
Создаёт CSV: product_id, product_name, price, quantity, expiry_date
"""

import csv
import os
import random
import sys
from datetime import datetime, timedelta

# Список возможных названий продуктов
PRODUCT_NAMES = [
    "Молоко", "Хлеб", "Яйца", "Масло", "Сыр", "Колбаса", "Мясо", "Рыба",
    "Овощи", "Фрукты", "Конфеты", "Печенье", "Сок", "Вода", "Чай", "Кофе",
    "Рис", "Гречка", "Макароны", "Соль", "Сахар", "Мука", "Кетчуп", "Майонез",
    "Йогурт", "Творог", "Сметана", "Кефир", "Пицца", "Пельмени"
]

def random_date(start_date: datetime, end_date: datetime) -> str:
    """Генерирует случайную дату в диапазоне и возвращает в формате YYYY-MM-DD"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randrange(days_between)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")

def generate_csv(output_path: str, size_gb: float = 1.1) -> str:
    """
    Пишет файл размером примерно size_gb гигабайт.
    Формат: product_id, product_name, price, quantity, expiry_date
    Возвращает путь к файлу.
    """
    target_bytes = int(size_gb * 1024 * 1024 * 1024)
    written = 0
    row_count = 0

    # Диапазон дат: от сегодня до +2 года
    today = datetime.now().date()
    start_date = datetime.combine(today, datetime.min.time())
    end_date = start_date + timedelta(days=730)  # 2 года

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Заголовок с 5 колонками
        writer.writerow(["product_id", "product_name", "price", "quantity", "expiry_date"])

        while written < target_bytes:
            product_id = row_count+1
            product_name = random.choice(PRODUCT_NAMES)
            price = round(random.uniform(1.0, 99999.99), 2)
            quantity = random.randint(0, 5000)
            expiry_date = random_date(start_date, end_date)
            
            line = f"{product_id},{product_name},{price},{quantity},{expiry_date}\n"
            f.write(line)
            written += len(line.encode("utf-8"))
            row_count += 1

    real_size = os.path.getsize(output_path)
    print(f"Готово: {output_path}")
    print(f"Строк: {row_count}, размер: {real_size / (1024**3):.2f} ГБ")
    return output_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data.csv"
    gb = float(sys.argv[2]) if len(sys.argv) > 2 else 1.1
    generate_csv(out, gb)