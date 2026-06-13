"""
Простой GUI для демонстрации внешней сортировки.
Запуск: python gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# добавляем папку python в путь
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(PROJECT_DIR, "python"))

from generate_data import generate_csv
from external_sort import external_sort, check_sorted, read_preview

# пробуем подключить C++ модуль через pybind11
try:
    import external_sort_cpp
    CPP_OK = True
except ImportError:
    CPP_OK = False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Внешняя сортировка — магазин")
        self.geometry("780x560")
        
        # Флаг состояния
        self.is_processing = False
        self.current_operation = ""

        default_csv = os.path.join(PROJECT_DIR, "data.csv")
        test_csv = os.path.join(PROJECT_DIR, "test.csv")
        if not os.path.isfile(default_csv) and os.path.isfile(test_csv):
            default_csv = test_csv

        self.input_file = tk.StringVar(value=default_csv)
        self.output_file = tk.StringVar(value=os.path.join(PROJECT_DIR, "sorted.csv"))
        self.sort_key = tk.StringVar(value="product_id")
        self.gen_size_gb = tk.StringVar(value="0.01")

        self._build_ui()

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ (определены ПЕРВЫМИ) ==========
    
    def _update_buttons_state(self):
        """Обновляет состояние всех кнопок в зависимости от is_processing"""
        if self.is_processing:
            self.btn_generate.state(["disabled"])
            self.btn_pick_input.state(["disabled"])
            self.btn_pick_output.state(["disabled"])
            self.btn_sort_python.state(["disabled"])
            self.btn_sort_cpp.state(["disabled"])
            self.btn_check.state(["disabled"])
            self.btn_preview_start.state(["disabled"])
            self.btn_preview_end.state(["disabled"])
            self.combo_key.state(["disabled"])
        else:
            self.btn_generate.state(["!disabled"])
            self.btn_pick_input.state(["!disabled"])
            self.btn_pick_output.state(["!disabled"])
            self.btn_sort_python.state(["!disabled"])
            if CPP_OK:
                self.btn_sort_cpp.state(["!disabled"])
            self.btn_check.state(["!disabled"])
            self.btn_preview_start.state(["!disabled"])
            self.btn_preview_end.state(["!disabled"])
            self.combo_key.state(["!disabled"])

    def _start_operation(self, operation_name: str):
        """Начинает операцию: блокирует интерфейс"""
        self.is_processing = True
        self.current_operation = operation_name
        self._update_buttons_state()
        self.log_insert(f"\n{'='*50}\n")
        self.log_insert(f"Начало операции: {operation_name}\n")
        self.log_insert(f"{'='*50}\n")

    def _finish_operation(self):
        """Завершает операцию: разблокирует интерфейс"""
        operation = self.current_operation
        self.is_processing = False
        self.current_operation = ""
        self._update_buttons_state()
        self.log_insert(f"\n{'='*50}\n")
        self.log_insert(f"Операция '{operation}' завершена\n")
        self.log_insert(f"{'='*50}\n\n")

    def log_insert(self, text: str):
        self.log.insert("end", text)
        self.log.see("end")

    # ========== МЕТОДЫ-ОБРАБОТЧИКИ (определены ДО _build_ui) ==========
    
    def pick_input(self):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if p:
            self.input_file.set(p)

    def pick_output(self):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        p = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if p:
            self.output_file.set(p)

    def on_generate(self):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        def work():
            try:
                gb = float(self.gen_size_gb.get())
                path = self.input_file.get()
                self.log_insert(f"Генерация {gb} ГБ -> {path} ...\n")
                generate_csv(path, gb)
                self.log_insert("Генерация завершена.\n")
            except Exception as e:
                self.log_insert(f"Ошибка: {e}\n")
            finally:
                self.after(0, self._finish_operation)

        self._start_operation("генерация")
        threading.Thread(target=work, daemon=True).start()

    def on_sort(self, engine: str):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        def work():
            inp = self.input_file.get()
            out = self.output_file.get()
            key = self.sort_key.get()

            if not os.path.isfile(inp):
                msg = (
                    f"Файл не найден:\n{inp}\n\n"
                    "Сначала нажми 'Сгенерировать' (шаг 1) или выбери готовый CSV."
                )
                self.log_insert(msg + "\n")
                self.after(0, lambda: messagebox.showwarning("Нет файла", msg))
                self.after(0, self._finish_operation)
                return

            self.log_insert(f"Сортировка ({engine}) по ключу '{key}'...\n")

            try:
                if engine == "python":
                    res = external_sort(inp, out, key)
                    self.log_insert(
                        f"  Разбиение: {res['split_seconds']} сек\n"
                        f"  Слияние:   {res['merge_seconds']} сек\n"
                        f"  Всего:     {res['total_seconds']} сек\n"
                        f"  Кусков:    {res.get('chunks', '?')}\n"
                    )
                else:
                    if not CPP_OK:
                        self.log_insert("C++ модуль не установлен.\n")
                        self.after(0, self._finish_operation)
                        return
                    res = external_sort_cpp.external_sort(inp, out, key)
                    self.log_insert(
                        f"  Разбиение: {res.split_seconds:.2f} сек\n"
                        f"  Слияние:   {res.merge_seconds:.2f} сек\n"
                        f"  Всего:     {res.total_seconds:.2f} сек\n"
                        f"  Кусков:    {res.chunks}\n"
                    )
            except Exception as e:
                self.log_insert(f"Ошибка: {e}\n")
            finally:
                self.after(0, self._finish_operation)

        self._start_operation(f"сортировка ({engine})")
        threading.Thread(target=work, daemon=True).start()

    def on_check(self):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        path = self.output_file.get()
        key = self.sort_key.get()

        if not os.path.isfile(path):
            self.log_insert("Выходной файл не найден.\n")
            return

        if CPP_OK:
            ok = external_sort_cpp.check_sorted(path, key, 500)
        else:
            ok, _ = check_sorted(path, key, 500)

        msg = "Сортировка верная" if ok else "Сортировка НЕ верная"
        self.log_insert(f"Проверка: {msg}\n\n")

    def on_preview(self, from_end: bool):
        if self.is_processing:
            messagebox.showwarning(
                "Операция выполняется",
                f"Сейчас идёт {self.current_operation}. Пожалуйста, дождитесь завершения."
            )
            return
            
        path = self.output_file.get()
        if not os.path.isfile(path):
            self.log_insert("Файл не найден.\n")
            return

        if CPP_OK:
            text = external_sort_cpp.read_preview(path, 15, from_end)
        else:
            text = read_preview(path, 15, from_end)

        where = "конец" if from_end else "начало"
        self.log_insert(f"--- {where} {path} ---\n{text}\n---\n\n")

    # ========== ПОСТРОЕНИЕ ИНТЕРФЕЙСА (определено ПОСЛЕДНИМ) ==========
    
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- генерация ---
        f1 = ttk.LabelFrame(self, text="1. Генерация data.csv")
        f1.pack(fill="x", **pad)

        ttk.Label(f1, text="Размер (ГБ):").grid(row=0, column=0, sticky="w")
        ttk.Entry(f1, textvariable=self.gen_size_gb, width=8).grid(row=0, column=1, sticky="w")
        self.btn_generate = ttk.Button(f1, text="Сгенерировать", command=self.on_generate)
        self.btn_generate.grid(row=0, column=2, padx=5)

        # --- файлы ---
        f2 = ttk.LabelFrame(self, text="2. Файлы")
        f2.pack(fill="x", **pad)

        ttk.Label(f2, text="Входной:").grid(row=0, column=0, sticky="w")
        ttk.Entry(f2, textvariable=self.input_file, width=60).grid(row=0, column=1)
        self.btn_pick_input = ttk.Button(f2, text="...", width=3, command=self.pick_input)
        self.btn_pick_input.grid(row=0, column=2)

        ttk.Label(f2, text="Выходной:").grid(row=1, column=0, sticky="w")
        ttk.Entry(f2, textvariable=self.output_file, width=60).grid(row=1, column=1)
        self.btn_pick_output = ttk.Button(f2, text="...", width=3, command=self.pick_output)
        self.btn_pick_output.grid(row=1, column=2)

        # --- сортировка ---
        f3 = ttk.LabelFrame(self, text="3. Сортировка")
        f3.pack(fill="x", **pad)

        ttk.Label(f3, text="Ключ:").grid(row=0, column=0)
        self.combo_key = ttk.Combobox(
            f3, textvariable=self.sort_key,
            values=["product_id", "product_name", "price", "quantity", "expiry_date"], 
            state="readonly", width=15
        )
        self.combo_key.grid(row=0, column=1, sticky="w")

        self.btn_sort_python = ttk.Button(f3, text="Сортировать (Python)", command=lambda: self.on_sort("python"))
        self.btn_sort_python.grid(row=0, column=2, padx=5)
        
        self.btn_sort_cpp = ttk.Button(f3, text="Сортировать (C++)", command=lambda: self.on_sort("cpp"))
        self.btn_sort_cpp.grid(row=0, column=3, padx=5)
        if not CPP_OK:
            self.btn_sort_cpp.state(["disabled"])

        # --- проверка ---
        f4 = ttk.LabelFrame(self, text="4. Проверка и просмотр")
        f4.pack(fill="x", **pad)

        self.btn_check = ttk.Button(f4, text="Проверить сортировку", command=self.on_check)
        self.btn_check.grid(row=0, column=0, padx=5)
        
        self.btn_preview_start = ttk.Button(f4, text="Начало файла", command=lambda: self.on_preview(False))
        self.btn_preview_start.grid(row=0, column=1, padx=5)
        
        self.btn_preview_end = ttk.Button(f4, text="Конец файла", command=lambda: self.on_preview(True))
        self.btn_preview_end.grid(row=0, column=2, padx=5)

        # --- лог ---
        self.log = scrolledtext.ScrolledText(self, height=18, font=("Consolas", 10))
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        status = "C++ модуль: OK" if CPP_OK else "C++ модуль: не собран (pip install .)"
        self.log_insert(f"Готов к работе. {status}\n")
        self.log_insert("Формат CSV: product_id, product_name, price, quantity, expiry_date\n")
        if not os.path.isfile(self.input_file.get()):
            self.log_insert(
                "Входной файл ещё не создан. Шаг 1: нажми 'Сгенерировать' "
                "(для отчёта поставь 1.1 ГБ, для теста — 0.01).\n\n"
            )
        else:
            self.log_insert(f"Входной файл: {self.input_file.get()}\n\n")
        
        self._update_buttons_state()


if __name__ == "__main__":
    app = App()
    app.mainloop()