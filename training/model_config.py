from transformers import T5Config

def get_config():
    config = T5Config(
        vocab_size=32128,      # Р±СѓРґРµС‚ РѕР±РЅРѕРІР»РµРЅ РїРѕРґ С‚РѕРєРµРЅРёР·Р°С‚РѕСЂ (resize later)
        d_model=256,           # СЃРєСЂС‹С‚С‹Р№ СЂР°Р·РјРµСЂ (embedding)
        d_ff=1024,             # СЂР°Р·РјРµСЂ FFN (РѕР±С‹С‡РЅРѕ 3-4*d_model)
        num_layers=4,          # encoder layers
        num_decoder_layers=4,  # decoder layers
        num_heads=4,
        dropout_rate=0.1,
        relative_attention_bias=True,
    )
    return config
