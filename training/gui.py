import tkinter as tk
from tkinter import scrolledtext, messagebox
from transformers import T5ForConditionalGeneration, AutoTokenizer
import threading

class DocstringGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Р“РµРЅРµСЂР°С‚РѕСЂ Docstring")
        self.root.geometry("800x600")

        # Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё
        self.setup_model()

        # РЎРѕР·РґР°РЅРёРµ РёРЅС‚РµСЂС„РµР№СЃР°
        self.create_widgets()

    def setup_model(self):
        """Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё РІ РѕС‚РґРµР»СЊРЅРѕРј РїРѕС‚РѕРєРµ"""
        self.model_loaded = False
        self.tokenizer = None
        self.model = None

        loading_thread = threading.Thread(target=self.load_model_thread)
        loading_thread.start()

    def load_model_thread(self):
        """РџРѕС‚РѕРє РґР»СЏ Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё"""
        try:
            model_path = "git_model"
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            self.model = T5ForConditionalGeneration.from_pretrained(model_path)
            self.model_loaded = True
            print("РњРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶РµРЅР° СѓСЃРїРµС€РЅРѕ")
        except Exception as e:
            print(f"РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё: {e}")

    def create_widgets(self):
        # Р—Р°РіРѕР»РѕРІРѕРє
        title_label = tk.Label(
            self.root,
            text="Р“РµРЅРµСЂР°С‚РѕСЂ Docstring РґР»СЏ Python РєРѕРґР°",
            font=("Arial", 16, "bold"),
            pady=10
        )
        title_label.pack()

        # РџРѕР»Рµ РІРІРѕРґР° РєРѕРґР° (РјРЅРѕРіРѕСЃС‚СЂРѕС‡РЅРѕРµ)
        tk.Label(self.root, text="Р’РІРµРґРёС‚Рµ РїРѕР»РЅС‹Р№ РєРѕРґ С„СѓРЅРєС†РёРё:", font=("Arial", 12)).pack(pady=10)

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

        # РљРЅРѕРїРєРё РїСЂРёРјРµСЂРѕРІ
        examples_frame = tk.Frame(self.root)
        examples_frame.pack(pady=10)

        # РџСЂРёРјРµСЂС‹ РїРѕР»РЅС‹С… С„СѓРЅРєС†РёР№
        examples = [
            {
                "name": "Р¤СѓРЅРєС†РёСЏ match1",
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
                "name": "РџСЂРѕСЃС‚Р°СЏ С„СѓРЅРєС†РёСЏ",
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
                "name": "Р¤Р°РєС‚РѕСЂРёР°Р»",
                "code": '''def calculate_factorial(n):
    if n == 0:
        return 1
    else:
        return n * calculate_factorial(n-1)'''
            },
            {
                "name": "РџРѕРёСЃРє РјР°РєСЃРёРјСѓРјР°",
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

        # РЎРѕР·РґР°РµРј РєРЅРѕРїРєРё РґР»СЏ РєР°Р¶РґРѕРіРѕ РїСЂРёРјРµСЂР°
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

        # РљРЅРѕРїРєР° РѕС‡РёСЃС‚РєРё
        clear_btn = tk.Button(
            examples_frame,
            text="РћС‡РёСЃС‚РёС‚СЊ",
            command=self.clear_text,
            bg="lightcoral",
            fg="white"
        )
        clear_btn.pack(side=tk.LEFT, padx=5)

        # РљРЅРѕРїРєР° РіРµРЅРµСЂР°С†РёРё
        self.generate_btn = tk.Button(
            self.root,
            text="рџЋЇ РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring",
            command=self.generate_docstring,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            state=tk.DISABLED,
            padx=20,
            pady=10
        )
        self.generate_btn.pack(pady=15)

        # РџРѕР»Рµ РІС‹РІРѕРґР° СЂРµР·СѓР»СЊС‚Р°С‚Р°
        result_frame = tk.Frame(self.root)
        result_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)

        tk.Label(result_frame, text="РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ docstring:", font=("Arial", 12)).pack(anchor="w")

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

        # РљРЅРѕРїРєР° РєРѕРїРёСЂРѕРІР°РЅРёСЏ
        copy_btn = tk.Button(
            result_frame,
            text="рџ“‹ РљРѕРїРёСЂРѕРІР°С‚СЊ docstring",
            command=self.copy_result,
            bg="#2196F3",
            fg="white"
        )
        copy_btn.pack(pady=5)

        # РЎС‚Р°С‚СѓСЃ Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё
        self.status_label = tk.Label(
            self.root,
            text="вЏі Р—Р°РіСЂСѓР·РєР° РјРѕРґРµР»Рё...",
            fg="blue",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=10)

        # РџСЂРѕРІРµСЂРєР° Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё
        self.check_model_loaded()

    def insert_example(self, example_code):
        """Р’СЃС‚Р°РІРєР° РїСЂРёРјРµСЂР° РІ РїРѕР»Рµ РІРІРѕРґР°"""
        self.code_text.delete("1.0", tk.END)
        self.code_text.insert("1.0", example_code)

    def clear_text(self):
        """РћС‡РёСЃС‚РєР° РїРѕР»РµР№ РІРІРѕРґР° Рё РІС‹РІРѕРґР°"""
        self.code_text.delete("1.0", tk.END)
        self.result_text.delete("1.0", tk.END)

    def copy_result(self):
        """РљРѕРїРёСЂРѕРІР°РЅРёРµ СЂРµР·СѓР»СЊС‚Р°С‚Р° РІ Р±СѓС„РµСЂ РѕР±РјРµРЅР°"""
        result = self.result_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            messagebox.showinfo("РЈСЃРїРµС…", "Docstring СЃРєРѕРїРёСЂРѕРІР°РЅ РІ Р±СѓС„РµСЂ РѕР±РјРµРЅР°!")

    def check_model_loaded(self):
        """РџСЂРѕРІРµСЂРєР° Р·Р°РіСЂСѓР·РєРё РјРѕРґРµР»Рё"""
        if self.model_loaded:
            self.status_label.config(text="вњ… РњРѕРґРµР»СЊ Р·Р°РіСЂСѓР¶РµРЅР° Рё РіРѕС‚РѕРІР° Рє СЂР°Р±РѕС‚Рµ!", fg="green")
            self.generate_btn.config(state=tk.NORMAL)
        else:
            self.root.after(1000, self.check_model_loaded)

    def generate_docstring(self):
        """Р“РµРЅРµСЂР°С†РёСЏ docstring"""
        if not self.model_loaded:
            messagebox.showerror("РћС€РёР±РєР°", "РњРѕРґРµР»СЊ РµС‰Рµ РЅРµ Р·Р°РіСЂСѓР¶РµРЅР°")
            return

        # РџРѕР»СѓС‡Р°РµРј РїРѕР»РЅС‹Р№ РєРѕРґ РёР· С‚РµРєСЃС‚РѕРІРѕРіРѕ РїРѕР»СЏ
        code = self.code_text.get("1.0", tk.END).strip()

        if not code:
            messagebox.showwarning("РџСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ", "РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РІРІРµРґРёС‚Рµ РєРѕРґ С„СѓРЅРєС†РёРё")
            return

        print(f"Р”Р»РёРЅР° РєРѕРґР° РґР»СЏ РѕР±СЂР°Р±РѕС‚РєРё: {len(code)} СЃРёРјРІРѕР»РѕРІ")
        print(f"РљРѕРґ: {code[:100]}...")  # Р›РѕРіРёСЂСѓРµРј РїРµСЂРІС‹Рµ 100 СЃРёРјРІРѕР»РѕРІ РґР»СЏ РѕС‚Р»Р°РґРєРё

        try:
            # РџРѕРєР°Р·С‹РІР°РµРј РёРЅРґРёРєР°С‚РѕСЂ Р·Р°РіСЂСѓР·РєРё
            self.generate_btn.config(state=tk.DISABLED, text="вЏі Р“РµРЅРµСЂР°С†РёСЏ...")
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", "Р“РµРЅРµСЂР°С†РёСЏ docstring...")

            # Р—Р°РїСѓСЃРєР°РµРј РіРµРЅРµСЂР°С†РёСЋ РІ РѕС‚РґРµР»СЊРЅРѕРј РїРѕС‚РѕРєРµ
            thread = threading.Thread(target=self.generate_thread, args=(code,))
            thread.start()

        except Exception as e:
            messagebox.showerror("РћС€РёР±РєР°", f"РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё: {str(e)}")
            self.generate_btn.config(state=tk.NORMAL, text="рџЋЇ РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring")

    def generate_thread(self, code):
        """РџРѕС‚РѕРє РґР»СЏ РіРµРЅРµСЂР°С†РёРё"""
        try:
            print(f"Р“РµРЅРµСЂРёСЂСѓРµРј docstring РґР»СЏ РєРѕРґР° РґР»РёРЅРѕР№ {len(code)} СЃРёРјРІРѕР»РѕРІ")

            # РџРѕРґРіРѕС‚РѕРІРєР° РІС…РѕРґРЅС‹С… РґР°РЅРЅС‹С…
            inputs = self.tokenizer(
                code,
                return_tensors="pt",
                truncation=True,
                max_length=512,  # РЈРІРµР»РёС‡РёР»Рё РјР°РєСЃРёРјР°Р»СЊРЅСѓСЋ РґР»РёРЅСѓ РґР»СЏ РїРѕР»РЅРѕРіРѕ РєРѕРґР°
                padding=True
            )

            # Р“РµРЅРµСЂР°С†РёСЏ
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=128,  # РЈРІРµР»РёС‡РёР»Рё РґР»СЏ Р±РѕР»РµРµ РїРѕРґСЂРѕР±РЅС‹С… docstring
                num_beams=5,
                early_stopping=True,
                no_repeat_ngram_size=3,
                pad_token_id=self.tokenizer.pad_token_id
            )

            # Р”РµРєРѕРґРёСЂРѕРІР°РЅРёРµ
            docstring = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # РћР±РЅРѕРІР»РµРЅРёРµ РёРЅС‚РµСЂС„РµР№СЃР° РІ РѕСЃРЅРѕРІРЅРѕРј РїРѕС‚РѕРєРµ
            self.root.after(0, self.update_result, docstring)

        except Exception as e:
            error_msg = f"РћС€РёР±РєР° РіРµРЅРµСЂР°С†РёРё: {str(e)}"
            print(error_msg)
            self.root.after(0, lambda: self.show_error(error_msg))

        finally:
            self.root.after(0, self.enable_generate_button)

    def update_result(self, docstring):
        """РћР±РЅРѕРІР»РµРЅРёРµ СЂРµР·СѓР»СЊС‚Р°С‚Р°"""
        self.result_text.delete("1.0", tk.END)
        formatted_docstring = f'"""{docstring}"""'
        self.result_text.insert("1.0", formatted_docstring)

        # РџРѕРєР°Р·С‹РІР°РµРј РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ СЂРµР·СѓР»СЊС‚Р°С‚Рµ
        print(f"РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ docstring: {docstring}")

    def show_error(self, error_msg):
        """РџРѕРєР°Р·Р°С‚СЊ РѕС€РёР±РєСѓ"""
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", f"РћС€РёР±РєР°: {error_msg}")
        messagebox.showerror("РћС€РёР±РєР°", error_msg)

    def enable_generate_button(self):
        """Р’РєР»СЋС‡РµРЅРёРµ РєРЅРѕРїРєРё РіРµРЅРµСЂР°С†РёРё"""
        self.generate_btn.config(state=tk.NORMAL, text="рџЋЇ РЎРіРµРЅРµСЂРёСЂРѕРІР°С‚СЊ Docstring")

if __name__ == "__main__":
    root = tk.Tk()
    app = DocstringGeneratorApp(root)
    root.mainloop()
