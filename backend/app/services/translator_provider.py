from deep_translator import GoogleTranslator


def translate_with_provider(
    source_text: str,
    source_lang: str,
    target_lang: str,
) -> tuple[str, str]:
    try:
        translated = GoogleTranslator(
            source=source_lang,
            target=target_lang,
        ).translate(source_text)
        return translated, "google"
    except Exception:
        return "[fallback] " + source_text, "fallback"
