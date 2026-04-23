from deep_translator import GoogleTranslator
translator = GoogleTranslator(source='auto', target='vi')
texts = ["Hello"] * 100
try:
    res = translator.translate_batch(texts)
    print(len(res))
except Exception as e:
    print("Error:", e)
