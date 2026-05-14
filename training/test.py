import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
from transformers import T5ForConditionalGeneration, AutoTokenizer
import threading

class SimpleDocstringGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Р“РµРЅРµСЂР°С‚РѕСЂ Docstring")
        self.root.geometry("600x400")

        # Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё
        self.setup_model()

        # РЎРѕР·РґР°РЅРёРµ РёРЅС‚РµСЂС„РµР№СЃР°
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
            print("РњРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶РµРЅР° СѓСЃРїРµС€РЅРѕ")
        except Exception as e:
            print(f"РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё: {e}")

    def create_widgets(self):
        # РџСЂРѕСЃС‚РѕРµ РїРѕР»Рµ РІРІРѕРґР° РґР»СЏ РѕРґРЅРѕР№ СЃС‚СЂРѕРєРё
        tk.Label(self.root, text="Р’РІРµРґРёС‚Рµ РЅР°Р·РІР°РЅРёРµ С„СѓРЅРєС†РёРё:").pack(pady=10)

        self.code_entry = tk.Entry(
            self.root,
            width=60,
            font=("Arial", 12)
        )
        self.code_entry.pack(pady=10)
        self.code_entry.bind('<Return>', lambda e: self.generate_docstring())

        # РџСЂРёРјРµСЂС‹ Р±С‹СЃС‚СЂРѕРіРѕ РІРІРѕРґР°
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

        # РљРЅРѕРїРєР° РіРµРЅРµСЂР°С†РёРё
        self.generate_btn = tk.Button(
            self.root,
            text="РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring",
            command=self.generate_docstring,
            bg="lightblue",
            font=("Arial", 12),
            state=tk.DISABLED
        )
        self.generate_btn.pack(pady=20)

        # РџРѕР»Рµ РІС‹РІРѕРґР° СЂРµР·СѓР»СЊС‚Р°С‚Р°
        tk.Label(self.root, text="РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ docstring:").pack(pady=5)

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

        # РЎС‚Р°С‚СѓСЃ
        self.status_label = tk.Label(self.root, text="Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё...", fg="blue")
        self.status_label.pack(pady=5)

        self.check_model_loaded()

    def check_model_loaded(self):
        if self.model_loaded:
            self.status_label.config(text="РњРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶РµРЅР° вњ“", fg="green")
            self.generate_btn.config(state=tk.NORMAL)
        else:
            self.root.after(1000, self.check_model_loaded)

    def generate_docstring(self):
        if not self.model_loaded:
            messagebox.showerror("РћС€РёР±РєР°", "РњРѕРґРµР»СЊ РµС‰Рµ РЅРµ Р·Р°РіСЂСѓР¶РµРЅР°")
            return

        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("РџСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ", "РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІРІРµРґРёС‚Рµ РєРѕРґ")
            return

        try:
            self.generate_btn.config(state=tk.DISABLED, text="Р“РµРЅРµСЂР°С†РёСЏ...")
            thread = threading.Thread(target=self.generate_thread, args=(code,))
            thread.start()

        except Exception as e:
            messagebox.showerror("РћС€РёР±РєР°", f"РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё: {str(e)}")
            self.generate_btn.config(state=tk.NORMAL, text="РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring")

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
            self.root.after(0, lambda: messagebox.showerror("РћС€РёР±РєР°", f"РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё: {str(e)}"))

        finally:
            self.root.after(0, self.enable_generate_button)

    def update_result(self, docstring):
        self.result_label.config(text=f'"""{docstring}"""')

    def enable_generate_button(self):
        self.generate_btn.config(state=tk.NORMAL, text="РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring")

if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleDocstringGeneratorApp(root)
    root.mainloop()
