import tkinter as tk
from tkinter import scrolledtext, messagebox
from transformers import T5Tokenizer, T5ForConditionalGeneration, T5Model, AutoTokenizer
import torch

# === Загрузка обученной модели ===
# Путь к твоей локальной модели
MODEL_PATH = "new_results_final"  # поменяй при необходимости

try:
    tokenizer = AutoTokenizer.from_pretrained("./scratch_t5_model")
    model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
except Exception as e:
    print("Ошибка при загрузке модели:", e)
    exit()


# === Функция генерации docstring ===
def generate_docstring():
    code = input_text.get("1.0", tk.END).strip()

    if not code:
        messagebox.showwarning("Ошибка", "Введите код функции!")
        return

    # Подготавливаем ввод
    input_ids = tokenizer(
        code,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=256
    ).input_ids.to(device)

    # Генерация
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            max_length=64,
            num_beams=4,
            early_stopping=True
        )

    # Расшифровка
    generated = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Очистка вывода
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, generated.strip())
    output_text.config(state=tk.DISABLED)


# === Интерфейс Tkinter ===
root = tk.Tk()
root.title("CodeT5: Генерация Docstring")
root.geometry("900x600")
root.configure(bg="#f4f4f4")

# Заголовок
title_label = tk.Label(
    root, text="Автоматическая генерация документации (CodeT5)",
    font=("Arial", 16, "bold"), bg="#f4f4f4", pady=10
)
title_label.pack()

# Поле для ввода кода
input_label = tk.Label(root, text="Введите код функции:", bg="#f4f4f4", anchor="w", font=("Arial", 12))
input_label.pack(fill="x", padx=20)

input_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=15, font=("Consolas", 11))
input_text.pack(padx=20, pady=10, fill="both", expand=True)

# Кнопка
generate_button = tk.Button(
    root,
    text="Сгенерировать docstring",
    command=generate_docstring,
    font=("Arial", 12, "bold"),
    bg="#0078d7",
    fg="white",
    padx=10,
    pady=5
)
generate_button.pack(pady=10)

# Поле вывода
output_label = tk.Label(root, text="Результат:", bg="#f4f4f4", anchor="w", font=("Arial", 12))
output_label.pack(fill="x", padx=20)

output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=8, font=("Consolas", 11))
output_text.pack(padx=20, pady=10, fill="both", expand=True)
output_text.config(state=tk.DISABLED)

# Запуск интерфейса
root.mainloop()
