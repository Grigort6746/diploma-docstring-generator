import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
from transformers import T5ForConditionalGeneration, AutoTokenizer
import threading

class SimpleDocstringGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Генератор Docstring")
        self.root.geometry("600x400")

        # Загрузка модели
        self.setup_model()

        # Создание интерфейса
        self.create_widgets()

    def setup_model(self):
        self.model_loaded = False
        self.tokenizer = None
        self.model = None

        loading_thread = threading.Thread(target=self.load_model_thread)
        loading_thread.start()

    def load_model_thread(self):
        try:
            model_path = "./m1"
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = T5ForConditionalGeneration.from_pretrained(model_path)
            self.model_loaded = True
            print("Модель загружена успешно")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")

    def create_widgets(self):
        # Простое поле ввода для одной строки
        tk.Label(self.root, text="Введите название функции:").pack(pady=10)

        self.code_entry = tk.Entry(
            self.root,
            width=60,
            font=("Arial", 12)
        )
        self.code_entry.pack(pady=10)
        self.code_entry.bind('<Return>', lambda e: self.generate_docstring())

        # Примеры быстрого ввода
        examples_frame = tk.Frame(self.root)
        examples_frame.pack(pady=10)

        examples = [
            "def add(a, b):",
            "def calculate_factorial(n):",
            "def find_max(numbers):",
            "def is_prime(number):"
        ]

        for example in examples:
            btn = tk.Button(
                examples_frame,
                text=example,
                command=lambda e=example: self.code_entry.insert(0, e),
                width=20
            )
            btn.pack(side=tk.LEFT, padx=5)

        # Кнопка генерации
        self.generate_btn = tk.Button(
            self.root,
            text="Сгенерировать Docstring",
            command=self.generate_docstring,
            bg="lightblue",
            font=("Arial", 12),
            state=tk.DISABLED
        )
        self.generate_btn.pack(pady=20)

        # Поле вывода результата
        tk.Label(self.root, text="Сгенерированный docstring:").pack(pady=5)

        self.result_label = tk.Label(
            self.root,
            text="",
            wraplength=500,
            justify=tk.LEFT,
            bg="lightyellow",
            font=("Courier", 10),
            relief=tk.SUNKEN,
            padx=10,
            pady=10
        )
        self.result_label.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        # Статус
        self.status_label = tk.Label(self.root, text="Загрузка модели...", fg="blue")
        self.status_label.pack(pady=5)

        self.check_model_loaded()

    def check_model_loaded(self):
        if self.model_loaded:
            self.status_label.config(text="Модель загружена ✓", fg="green")
            self.generate_btn.config(state=tk.NORMAL)
        else:
            self.root.after(1000, self.check_model_loaded)

    def generate_docstring(self):
        if not self.model_loaded:
            messagebox.showerror("Ошибка", "Модель еще не загружена")
            return

        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("Предупреждение", "Пожалуйста, введите код")
            return

        try:
            self.generate_btn.config(state=tk.DISABLED, text="Генерация...")
            thread = threading.Thread(target=self.generate_thread, args=(code,))
            thread.start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка генерации: {str(e)}")
            self.generate_btn.config(state=tk.NORMAL, text="Сгенерировать Docstring")

    def generate_thread(self, code):
        try:
            inputs = self.tokenizer(
                code,
                return_tensors="pt",
                truncation=True,
                max_length=256,
                padding=True
            )

            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=64,
                num_beams=5,
                early_stopping=True,
                no_repeat_ngram_size=3,
                pad_token_id=self.tokenizer.pad_token_id
            )

            docstring = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            self.root.after(0, self.update_result, docstring)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка генерации: {str(e)}"))

        finally:
            self.root.after(0, self.enable_generate_button)

    def update_result(self, docstring):
        self.result_label.config(text=f'"""{docstring}"""')

    def enable_generate_button(self):
        self.generate_btn.config(state=tk.NORMAL, text="Сгенерировать Docstring")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleDocstringGeneratorApp(root)
    root.mainloop()