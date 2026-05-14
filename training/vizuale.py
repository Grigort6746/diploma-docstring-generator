import json
import matplotlib.pyplot as plt

# === 1. Загрузка данных ===
with open("git_results/checkpoint-16716/trainer_state.json", "r", encoding="utf-8") as f:
    data = json.load(f)

logs = data["log_history"]

# === 2. Извлечение метрик ===
steps = [x["step"] for x in logs if "loss" in x]
losses = [x["loss"] for x in logs if "loss" in x]

eval_steps = [x["step"] for x in logs if "eval_loss" in x]
eval_loss = [x["eval_loss"] for x in logs if "eval_loss" in x]
eval_bleu = [x["eval_bleu"] for x in logs if "eval_bleu" in x]
eval_rouge1 = [x["eval_rouge1"] for x in logs if "eval_rouge1" in x]
eval_rougeL = [x["eval_rougeL"] for x in logs if "eval_rougeL" in x]

# === 3. Построение графика потерь ===
plt.figure(figsize=(10, 6))
plt.plot(steps, losses, label="Training Loss", linewidth=1.5)
plt.plot(eval_steps, eval_loss, label="Validation Loss", linewidth=1.5)
plt.xlabel("Шаги обучения")
plt.ylabel("Потери (Loss)")
plt.title("Динамика функции потерь при обучении модели")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# === 4. Построение графиков метрик ===
plt.figure(figsize=(10, 6))
plt.plot(eval_steps, eval_bleu, marker="o", label="BLEU")
plt.plot(eval_steps, eval_rouge1, marker="o", label="ROUGE-1")
plt.plot(eval_steps, eval_rougeL, marker="o", label="ROUGE-L")
plt.xlabel("Шаги обучения")
plt.ylabel("Значение метрики")
plt.title("Изменение метрик качества модели по эпохам")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
