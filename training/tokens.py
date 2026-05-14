from transformers import AutoTokenizer
import pandas as pd

# Путь к твоей модели
MODEL_PATH = "git_model"

# Загружаем токенизатор
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# Получаем словарь токенов
vocab = tokenizer.get_vocab()

# Преобразуем в DataFrame для удобства
df = pd.DataFrame(list(vocab.items()), columns=["token", "token_id"])

# Сортируем по id
df = df.sort_values("token_id")

# Сохраняем таблицу в CSV
df.to_csv("token_table.csv", index=False, encoding="utf-8")

print("✅ Таблица токенов сохранена: token_table.csv")
print(df.head(10))
