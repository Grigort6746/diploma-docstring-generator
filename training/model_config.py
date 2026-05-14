from transformers import T5Config

def get_config():
    config = T5Config(
        vocab_size=32128,      # будет обновлен под токенизатор (resize later)
        d_model=256,           # скрытый размер (embedding)
        d_ff=1024,             # размер FFN (обычно 3-4*d_model)
        num_layers=4,          # encoder layers
        num_decoder_layers=4,  # decoder layers
        num_heads=4,
        dropout_rate=0.1,
        relative_attention_bias=True,
    )
    return config