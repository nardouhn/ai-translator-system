from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='auto', target='vi')
texts = ["Hello", "World", "This is a test"]
translated = translator.translate_batch(texts)
print(translated)
