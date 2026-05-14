from transformers import AutoTokenizer
import pandas as pd

# РџСѓС‚СЊ Рє С‚РІРѕРµР№ РјРѕРґРµР»Рё
MODEL_PATH = "git_model"

# Р—Р°РіСЂСѓР¶Р°РµРј С‚РѕРєРµРЅРёР·Р°С‚РѕСЂ
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# РџРѕР»СѓС‡Р°РµРј СЃР»РѕРІР°СЂСЊ С‚РѕРєРµРЅРѕРІ
vocab = tokenizer.get_vocab()

# РџСЂРµРѕР±СЂР°Р·СѓРµРј РІ DataFrame РґР»СЏ СѓРґРѕР±СЃС‚РІР°
df = pd.DataFrame(list(vocab.items()), columns=["token", "token_id"])

# РЎРѕСЂС‚РёСЂСѓРµРј РїРѕ id
df = df.sort_values("token_id")

# РЎРѕС…СЂР°РЅСЏРµРј С‚Р°Р±Р»РёС†Сѓ РІ CSV
df.to_csv("token_table.csv", index=False, encoding="utf-8")

print("вњ… РўР°Р±Р»РёС†Р° С‚РѕРєРµРЅРѕРІ СЃРѕС…СЂР°РЅРµРЅР°: token_table.csv")
print(df.head(10))
