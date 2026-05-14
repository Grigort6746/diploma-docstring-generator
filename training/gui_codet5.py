import tkinter as tk
from tkinter import scrolledtext, messagebox
from transformers import T5Tokenizer, T5ForConditionalGeneration, T5Model, AutoTokenizer
import torch

# === Р—Р°РіСЂСѓР·РєР° РѕР±СѓС‡РµРЅРЅРѕР№ РјРѕРґРµР»Рё ===
# РџСѓС‚СЊ Рє С‚РІРѕРµР№ Р»РѕРєР°Р»СЊРЅРѕР№ РјРѕРґРµР»Рё
MODEL_PATH = "new_results_final"  # РїРѕРјРµРЅСЏР№ РїСЂРё РЅРµРѕР±С…РѕРґРёРјРѕСЃС‚Рё

try:
    tokenizer = AutoTokenizer.from_pretrained("./scratch_t5_model")
    model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
except Exception as e:
    print("РћС€РёР±РєР° РїСЂРё Р·Р°РіСЂСѓР·РєРµ РјРѕРґРµР»Рё:", e)
    exit()


# === Р¤СѓРЅРєС†РёСЏ РіРµРЅРµСЂР°С†РёРё docstring ===
def generate_docstring():
    code = input_text.get("1.0", tk.END).strip()

    if not code:
        messagebox.showwarning("РћС€РёР±РєР°", "Р’РІРµРґРёС‚Рµ РєРѕРґ С„СѓРЅРєС†РёРё!")
        return

    # РџРѕРґРіРѕС‚Р°РІР»РёРІР°РµРј РІРІРѕРґ
    input_ids = tokenizer(
        code,
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=256
    ).input_ids.to(device)

    # Р“РµРЅРµСЂР°С†РёСЏ
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            max_length=64,
            num_beams=4,
            early_stopping=True
        )

    # Р Р°СЃС€РёС„СЂРѕРІРєР°
    generated = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # РћС‡РёСЃС‚РєР° РІС‹РІРѕРґР°
    output_text.config(state=tk.NORMAL)
    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, generated.strip())
    output_text.config(state=tk.DISABLED)


# === РРЅС‚РµСЂС„РµР№СЃ Tkinter ===
root = tk.Tk()
root.title("CodeT5: Р“РµРЅРµСЂР°С†РёСЏ Docstring")
root.geometry("900x600")
root.configure(bg="#f4f4f4")

# Р—Р°РіРѕР»РѕРІРѕРє
title_label = tk.Label(
    root, text="РђРІС‚РѕРјР°С‚РёС‡РµСЃРєР°СЏ РіРµРЅРµСЂР°С†РёСЏ РґРѕРєСѓРјРµРЅС‚Р°С†РёРё (CodeT5)",
    font=("Arial", 16, "bold"), bg="#f4f4f4", pady=10
)
title_label.pack()

# РџРѕР»Рµ РґР»СЏ РІРІРѕРґР° РєРѕРґР°
input_label = tk.Label(root, text="Р’РІРµРґРёС‚Рµ РєРѕРґ С„СѓРЅРєС†РёРё:", bg="#f4f4f4", anchor="w", font=("Arial", 12))
input_label.pack(fill="x", padx=20)

input_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=15, font=("Consolas", 11))
input_text.pack(padx=20, pady=10, fill="both", expand=True)

# РљРЅРѕРїРєР°
generate_button = tk.Button(
    root,
    text="РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ docstring",
    command=generate_docstring,
    font=("Arial", 12, "bold"),
    bg="#0078d7",
    fg="white",
    padx=10,
    pady=5
)
generate_button.pack(pady=10)

# РџРѕР»Рµ РІС‹РІРѕРґР°
output_label = tk.Label(root, text="Р РµР·СѓР»СЊС‚Р°С‚:", bg="#f4f4f4", anchor="w", font=("Arial", 12))
output_label.pack(fill="x", padx=20)

output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=8, font=("Consolas", 11))
output_text.pack(padx=20, pady=10, fill="both", expand=True)
output_text.config(state=tk.DISABLED)

# Р—Р°РїСѓСЃРє РёРЅС‚РµСЂС„РµР№СЃР°
root.mainloop()
