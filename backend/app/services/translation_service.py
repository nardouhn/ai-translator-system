import hashlib

from sqlalchemy.orm import Session as DBSession

from app.db.models import Domain, DomainNameEnum, Language, Translation
from app.services.cache_service import get_cached_translation, set_cached_translation
from app.services.translator_provider import translate_with_provider


def _get_or_create_language(db: DBSession, lang_code: str) -> Language:
    normalized_code = lang_code.strip().lower()
    language = db.query(Language).filter(Language.lang_code == normalized_code).first()
    if language:
        return language

    language = Language(
        lang_code=normalized_code,
        lang_name=normalized_code.upper(),
    )
    db.add(language)
    db.flush()
    return language


def _get_or_create_domain(db: DBSession, domain: str | None) -> Domain:
    domain_value = (domain or DomainNameEnum.general.value).strip().lower()
    allowed_values = {item.value for item in DomainNameEnum}
    if domain_value not in allowed_values:
        domain_value = DomainNameEnum.general.value

    domain_row = db.query(Domain).filter(Domain.domain_name == domain_value).first()
    if domain_row:
        return domain_row

    domain_row = Domain(domain_name=DomainNameEnum(domain_value))
    db.add(domain_row)
    db.flush()
    return domain_row


def translate_text(
    db,
    session_id: str,
    source_text: str,
    source_lang: str,
    target_lang: str,
    domain: str | None,
    auto_commit: bool = True,
):
    cached_value = get_cached_translation(source_lang, target_lang, source_text)
    if cached_value is not None:
        return {
            "translated_text": cached_value,
            "translation_id": None,
            "from_cache": True,
        }

    translated_text, provider = translate_with_provider(
        source_text,
        source_lang,
        target_lang,
    )

    source_language = _get_or_create_language(db, source_lang)
    target_language = _get_or_create_language(db, target_lang)
    domain_row = _get_or_create_domain(db, domain)

    translation_data = {
        "session_id": session_id,
        "source_text": source_text,
        "translated_text": translated_text,
        "source_lang": source_language.lang_id,
        "target_lang": target_language.lang_id,
        "domain_id": domain_row.domain_id,
        "text_hash": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    }
    # Keep compatibility if DB column is still named model_name.
    if hasattr(Translation, "provider"):
        translation_data["provider"] = provider
    else:
        translation_data["model_name"] = provider

    translation = Translation(
        **translation_data,
    )
    db.add(translation)
    if auto_commit:
        db.commit()
        db.refresh(translation)

    set_cached_translation(source_lang, target_lang, source_text, translated_text)

    return {
        "translated_text": translated_text,
        "translation_id": getattr(translation, "id", translation.trans_id),
        "from_cache": False,
    }
