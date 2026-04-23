import time
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='auto', target='vi')
texts = ["Hello World"] * 50

start = time.time()
for t in texts:
    translator.translate(t)
end_seq = time.time() - start

start = time.time()
translator.translate_batch(texts)
end_batch = time.time() - start

print(f"Seq: {end_seq}, Batch: {end_batch}")
