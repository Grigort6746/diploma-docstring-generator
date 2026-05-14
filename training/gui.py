import tkinter as tk
from tkinter import scrolledtext, messagebox
from transformers import T5ForConditionalGeneration, AutoTokenizer
import threading

class DocstringGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Генератор Docstring")
        self.root.geometry("800x600")

        # Загрузка модели
        self.setup_model()

        # Создание интерфейса
        self.create_widgets()

    def setup_model(self):
        """Загрузка модели в отдельном потоке"""
        self.model_loaded = False
        self.tokenizer = None
        self.model = None

        loading_thread = threading.Thread(target=self.load_model_thread)
        loading_thread.start()

    def load_model_thread(self):
        """Поток для загрузки модели"""
        try:
            model_path = "git_model"
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = T5ForConditionalGeneration.from_pretrained(model_path)
            self.model_loaded = True
            print("Модель загружена успешно")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")

    def create_widgets(self):
        # Заголовок
        title_label = tk.Label(
            self.root,
            text="Генератор Docstring для Python кода",
            font=("Arial", 16, "bold"),
            pady=10
        )
        title_label.pack()

        # Поле ввода кода (многострочное)
        tk.Label(self.root, text="Введите полный код функции:", font=("Arial", 12)).pack(pady=10)

        self.code_text = scrolledtext.ScrolledText(
            self.root,
            width=80,
            height=12,
            font=("Courier", 10),
            wrap=tk.WORD,
            relief=tk.SUNKEN,
            bd=2
        )
        self.code_text.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)

        # Кнопки примеров
        examples_frame = tk.Frame(self.root)
        examples_frame.pack(pady=10)

        # Примеры полных функций
        examples = [
            {
                "name": "Функция match1",
                "code": '''def match1(text, *patterns):
    if len(patterns) == 1:
        pattern = patterns[0]
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        else:
            return None
    else:
        ret = []
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                ret.append(match.group(1))
        return ret'''
            },
            {
                "name": "Простая функция",
                "code": '''def checkDnsWildcard(self, target: str) -> bool:
    if not target:
        return False
    randpool = 'bcdfghjklmnpqrstvwxyz3456789'
    randhost = ''.join([random.SystemRandom().choice(randpool) for x in range(10)])
    if not self.resolveHost(randhost + '.' + target):
        return False
    return True'''
            },
            {
                "name": "Факториал",
                "code": '''def calculate_factorial(n):
    if n == 0:
        return 1
    else:
        return n * calculate_factorial(n-1)'''
            },
            {
                "name": "Поиск максимума",
                "code": '''def find_max(numbers):
    if not numbers:
        return None
    max_num = numbers[0]
    for num in numbers:
        if num > max_num:
            max_num = num
    return max_num'''
            }
        ]

        # Создаем кнопки для каждого примера
        for example in examples:
            btn = tk.Button(
                examples_frame,
                text=example["name"],
                command=lambda e=example["code"]: self.insert_example(e),
                width=15,
                relief=tk.RAISED,
                bd=2
            )
            btn.pack(side=tk.LEFT, padx=5)

        # Кнопка очистки
        clear_btn = tk.Button(
            examples_frame,
            text="Очистить",
            command=self.clear_text,
            bg="lightcoral",
            fg="white"
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Кнопка генерации
        self.generate_btn = tk.Button(
            self.root,
            text="🎯 Сгенерировать Docstring",
            command=self.generate_docstring,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            state=tk.DISABLED,
            padx=20,
            pady=10
        )
        self.generate_btn.pack(pady=15)

        # Поле вывода результата
        result_frame = tk.Frame(self.root)
        result_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        tk.Label(result_frame, text="Сгенерированный docstring:", font=("Arial", 12)).pack(anchor="w")

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            width=80,
            height=6,
            font=("Courier", 11),
            bg="#FFF9C4",
            wrap=tk.WORD,
            relief=tk.SUNKEN,
            bd=2
        )
        self.result_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # Кнопка копирования
        copy_btn = tk.Button(
            result_frame,
            text="📋 Копировать docstring",
            command=self.copy_result,
            bg="#2196F3",
            fg="white"
        )
        copy_btn.pack(pady=5)

        # Статус загрузки модели
        self.status_label = tk.Label(
            self.root,
            text="⏳ Загрузка модели...",
            fg="blue",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=10)

        # Проверка загрузки модели
        self.check_model_loaded()

    def insert_example(self, example_code):
        """Вставка примера в поле ввода"""
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", example_code)

    def clear_text(self):
        """Очистка полей ввода и вывода"""
        self.code_text.delete("1.0", tk.END)
        self.result_text.delete("1.0", tk.END)

    def copy_result(self):
        """Копирование результата в буфер обмена"""
        result = self.result_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            messagebox.showinfo("Успех", "Docstring скопирован в буфер обмена!")

    def check_model_loaded(self):
        """Проверка загрузки модели"""
        if self.model_loaded:
            self.status_label.config(text="✅ Модель загружена и готова к работе!", fg="green")
            self.generate_btn.config(state=tk.NORMAL)
        else:
            self.root.after(1000, self.check_model_loaded)

    def generate_docstring(self):
        """Генерация docstring"""
        if not self.model_loaded:
            messagebox.showerror("Ошибка", "Модель еще не загружена")
            return

        # Получаем полный код из текстового поля
        code = self.code_text.get("1.0", tk.END).strip()

        if not code:
            messagebox.showwarning("Предупреждение", "Пожалуйста, введите код функции")
            return

        print(f"Длина кода для обработки: {len(code)} символов")
        print(f"Код: {code[:100]}...")  # Логируем первые 100 символов для отладки

        try:
            # Показываем индикатор загрузки
            self.generate_btn.config(state=tk.DISABLED, text="⏳ Генерация...")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", "Генерация docstring...")

            # Запускаем генерацию в отдельном потоке
            thread = threading.Thread(target=self.generate_thread, args=(code,))
            thread.start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации: {str(e)}")
            self.generate_btn.config(state=tk.NORMAL, text="🎯 Сгенерировать Docstring")

    def generate_thread(self, code):
        """Поток для генерации"""
        try:
            print(f"Генерируем docstring для кода длиной {len(code)} символов")

            # Подготовка входных данных
            inputs = self.tokenizer(
                code,
                return_tensors="pt",
                truncation=True,
                max_length=512,  # Увеличили максимальную длину для полного кода
                padding=True
            )

            # Генерация
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=128,  # Увеличили для более подробных docstring
                num_beams=5,
                early_stopping=True,
                no_repeat_ngram_size=3,
                pad_token_id=self.tokenizer.pad_token_id
            )

            # Декодирование
            docstring = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Обновление интерфейса в основном потоке
            self.root.after(0, self.update_result, docstring)

        except Exception as e:
            error_msg = f"Ошибка генерации: {str(e)}"
            print(error_msg)
            self.root.after(0, lambda: self.show_error(error_msg))

        finally:
            self.root.after(0, self.enable_generate_button)

    def update_result(self, docstring):
        """Обновление результата"""
        self.result_text.delete("1.0", tk.END)
        formatted_docstring = f'"""{docstring}"""'
        self.result_text.insert("1.0", formatted_docstring)

        # Показываем информацию о результате
        print(f"Сгенерированный docstring: {docstring}")

    def show_error(self, error_msg):
        """Показать ошибку"""
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"Ошибка: {error_msg}")
        messagebox.showerror("Ошибка", error_msg)

    def enable_generate_button(self):
        """Включение кнопки генерации"""
        self.generate_btn.config(state=tk.NORMAL, text="🎯 Сгенерировать Docstring")

if __name__ == "__main__":
    root = tk.Tk()
    app = DocstringGeneratorApp(root)
    root.mainloop()