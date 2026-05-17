from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from bs4 import BeautifulSoup
from datasets import load_dataset

LOGGER = logging.getLogger(__name__)


@dataclass
class HFSource:
    dataset_name: str
    config_name: Optional[str]
    split: str
    source_lang: str
    target_lang: str
    sample_limit: Optional[int] = None


@dataclass
class CrawlerConfig:
    output_dir: Path = Path("raw_dataset")
    hf_sources: List[HFSource] = field(
        default_factory=lambda: [
            HFSource("ncduy/mt-en-vi", None, "train", "en", "vi", 200000),
            HFSource("talmp/en-vi-translation", None, "train", "en", "vi", 200000),
        ]
    )
    bilingual_web_urls: Sequence[str] = field(default_factory=list)
    github_readme_queries: Sequence[str] = field(
        default_factory=lambda: [
            "bilingual english vietnamese README programming",
            "API tai lieu vietnamese english",
        ]
    )
    github_max_repos_per_query: int = 20
    github_token: Optional[str] = None
    hf_streaming: bool = True


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_pair_from_record(record: Dict, source_lang: str, target_lang: str) -> Optional[Tuple[str, str]]:
    if "translation" in record and isinstance(record["translation"], dict):
        src = record["translation"].get(source_lang)
        tgt = record["translation"].get(target_lang)
        if src and tgt:
            return str(src).strip(), str(tgt).strip()

    if source_lang in record and target_lang in record:
        src = record.get(source_lang)
        tgt = record.get(target_lang)
        if src and tgt:
            return str(src).strip(), str(tgt).strip()

    for maybe_pair_key in ["translations", "pair", "sentence_pair"]:
        if maybe_pair_key in record and isinstance(record[maybe_pair_key], dict):
            src = record[maybe_pair_key].get(source_lang)
            tgt = record[maybe_pair_key].get(target_lang)
            if src and tgt:
                return str(src).strip(), str(tgt).strip()

    # Try translation dictionaries that use non-standard language tags like en_XX / vi_VN.
    for key in ["translation", "translations", "pair", "sentence_pair"]:
        val = record.get(key)
        if isinstance(val, dict):
            src = _pick_lang_value_from_dict(val, source_lang)
            tgt = _pick_lang_value_from_dict(val, target_lang)
            if src and tgt:
                return src, tgt

    # Handle common field-name variants from public translation datasets.
    alias_map = {
        "en": ["en", "eng", "english", "source", "src", "text_en", "sentence_en"],
        "vi": ["vi", "vie", "vietnamese", "target", "tgt", "text_vi", "sentence_vi"],
    }
    src_aliases = alias_map.get(source_lang, [source_lang])
    tgt_aliases = alias_map.get(target_lang, [target_lang])
    for src_key in src_aliases:
        for tgt_key in tgt_aliases:
            if src_key in record and tgt_key in record:
                src = record.get(src_key)
                tgt = record.get(tgt_key)
                if src and tgt:
                    return str(src).strip(), str(tgt).strip()

    # Auto-detect EN/VI columns by key names for unknown schemas.
    src = _pick_lang_value_from_dict(record, source_lang)
    tgt = _pick_lang_value_from_dict(record, target_lang)
    if src and tgt:
        return src, tgt

    # Last resort: if record contains exactly two textual fields, use them in declared source/target order.
    str_items = [(k, v) for k, v in record.items() if isinstance(v, str) and v.strip()]
    if len(str_items) == 2:
        values = {k.lower(): str(v).strip() for k, v in str_items}
        src_guess = _pick_lang_value_from_dict(values, source_lang)
        tgt_guess = _pick_lang_value_from_dict(values, target_lang)
        if src_guess and tgt_guess:
            return src_guess, tgt_guess

    return None


def _pick_lang_value_from_dict(obj: Dict, lang: str) -> Optional[str]:
    lang = lang.lower()
    if lang == "en":
        hints = ["en", "eng", "english", "src", "source"]
    elif lang == "vi":
        hints = ["vi", "vie", "vietnamese", "tgt", "target"]
    else:
        hints = [lang]

    for key, value in obj.items():
        if value is None:
            continue
        key_l = str(key).lower()
        if any(key_l == h or key_l.startswith(h + "_") or ("_" + h) in key_l for h in hints):
            text = str(value).strip()
            if text:
                return text

    return None


def crawl_huggingface_sources(config: CrawlerConfig) -> pd.DataFrame:
    rows: List[Dict] = []

    for source in config.hf_sources:
        try:
            LOGGER.info(
                "Loading HF dataset=%s config=%s split=%s",
                source.dataset_name,
                source.config_name,
                source.split,
            )
            ds = load_dataset(
                source.dataset_name,
                source.config_name,
                split=source.split,
                trust_remote_code=False,
                streaming=config.hf_streaming,
            )
        except Exception as exc:
            LOGGER.warning("Skipping source %s due to error: %s", source.dataset_name, exc)
            continue

        try:
            for idx, record in enumerate(ds):
                if source.sample_limit is not None and idx >= source.sample_limit:
                    break

                pair = _extract_pair_from_record(record, source.source_lang, source.target_lang)
                if not pair:
                    continue

                en_text, vi_text = pair
                rows.append(
                    {
                        "en": en_text,
                        "vi": vi_text,
                        "source": f"hf:{source.dataset_name}:{source.config_name or 'default'}",
                        "metadata": json.dumps(
                            {
                                "split": source.split,
                                "source_lang": source.source_lang,
                                "target_lang": source.target_lang,
                            },
                            ensure_ascii=True,
                        ),
                    }
                )
        except Exception as exc:
            LOGGER.warning(
                "Iteration failed for source %s (stream/network/schema issue): %s",
                source.dataset_name,
                exc,
            )
            continue

    return pd.DataFrame(rows)


def _download_text(url: str, timeout_sec: int = 15) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (data-pipeline-bot)"})
    with urlopen(req, timeout=timeout_sec) as response:
        return response.read().decode("utf-8", errors="ignore")


def crawl_bilingual_web_pages(urls: Sequence[str]) -> pd.DataFrame:
    """
    Crawl bilingual web pages where EN and VI blocks are in the same page.
    Pairing strategy is heuristic by sentence order after extracting candidate blocks.
    """
    rows: List[Dict] = []

    for url in urls:
        try:
            html = _download_text(url)
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text("\n", strip=True)
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            LOGGER.warning("Failed to crawl url=%s error=%s", url, exc)
            continue

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        en_candidates = [ln for ln in lines if re.search(r"[A-Za-z]", ln)]
        vi_candidates = [ln for ln in lines if re.search(r"[a-zA-Z]", ln)]

        en_sents: List[str] = []
        vi_sents: List[str] = []

        for ln in en_candidates:
            en_sents.extend(_split_sentences(ln))
        for ln in vi_candidates:
            vi_sents.extend(_split_sentences(ln))

        pair_count = min(len(en_sents), len(vi_sents))
        for i in range(pair_count):
            rows.append(
                {
                    "en": en_sents[i],
                    "vi": vi_sents[i],
                    "source": f"web:{url}",
                    "metadata": json.dumps({"url": url, "pairing": "heuristic-order"}, ensure_ascii=True),
                }
            )

    return pd.DataFrame(rows)


def _fetch_json(url: str, token: Optional[str] = None, timeout_sec: int = 15) -> Dict:
    headers = {"User-Agent": "Mozilla/5.0 (data-pipeline-bot)", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def crawl_github_bilingual_readmes(
    queries: Sequence[str],
    max_repos_per_query: int,
    token: Optional[str] = None,
) -> pd.DataFrame:
    rows: List[Dict] = []

    for query in queries:
        search_url = (
            "https://api.github.com/search/repositories"
            f"?q={query.replace(' ', '+')}&sort=stars&order=desc&per_page={max_repos_per_query}"
        )

        try:
            payload = _fetch_json(search_url, token=token)
        except Exception as exc:
            LOGGER.warning("GitHub query failed for '%s': %s", query, exc)
            continue

        items = payload.get("items", [])
        for item in items:
            full_name = item.get("full_name")
            default_branch = item.get("default_branch", "main")
            if not full_name:
                continue

            raw_readme_url = (
                f"https://raw.githubusercontent.com/{full_name}/{default_branch}/README.md"
            )
            try:
                readme = _download_text(raw_readme_url)
            except Exception:
                continue

            # Heuristic extraction for bilingual README sections.
            en_block = _extract_markdown_lang_block(readme, "english")
            vi_block = _extract_markdown_lang_block(readme, "vietnamese")
            if not en_block or not vi_block:
                continue

            en_sents = _split_sentences(en_block)
            vi_sents = _split_sentences(vi_block)
            for i in range(min(len(en_sents), len(vi_sents))):
                rows.append(
                    {
                        "en": en_sents[i],
                        "vi": vi_sents[i],
                        "source": f"github:{full_name}",
                        "metadata": json.dumps(
                            {
                                "repo": full_name,
                                "readme": raw_readme_url,
                                "pairing": "section-order",
                            },
                            ensure_ascii=True,
                        ),
                    }
                )

    return pd.DataFrame(rows)


def _extract_markdown_lang_block(markdown_text: str, lang_hint: str) -> str:
    pattern = re.compile(
        rf"(?is)(?:^|\n)#+\s*.*{re.escape(lang_hint)}.*?\n(.*?)(?=\n#+\s|\Z)"
    )
    match = pattern.search(markdown_text)
    return match.group(1).strip() if match else ""


def merge_raw_sources(dataframes: Iterable[pd.DataFrame]) -> pd.DataFrame:
    frames = [df for df in dataframes if df is not None and not df.empty]
    if not frames:
        return pd.DataFrame(columns=["en", "vi", "source", "metadata"])

    merged = pd.concat(frames, ignore_index=True)
    merged = merged[["en", "vi", "source", "metadata"]]
    return merged


def write_raw_dataset(df: pd.DataFrame, output_dir: Path) -> None:
    _ensure_dir(output_dir)
    parquet_path = output_dir / "raw_dataset.parquet"
    jsonl_path = output_dir / "raw_dataset.jsonl"

    df.to_parquet(parquet_path, index=False)

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in df.to_dict(orient="records"):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    LOGGER.info("Wrote raw dataset rows=%d parquet=%s jsonl=%s", len(df), parquet_path, jsonl_path)


def run_crawler(config: CrawlerConfig) -> pd.DataFrame:
    hf_df = crawl_huggingface_sources(config)
    web_df = crawl_bilingual_web_pages(config.bilingual_web_urls)
    gh_df = crawl_github_bilingual_readmes(
        config.github_readme_queries,
        max_repos_per_query=config.github_max_repos_per_query,
        token=config.github_token,
    )

    raw_df = merge_raw_sources([hf_df, web_df, gh_df])
    write_raw_dataset(raw_df, config.output_dir)
    return raw_df


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl EN-VI bilingual raw data")
    parser.add_argument("--output-dir", default="raw_dataset", help="Output folder for raw data")
    parser.add_argument(
        "--github-token",
        default=None,
        help="Optional GitHub token for higher API limit",
    )
    parser.add_argument(
        "--web-url",
        action="append",
        default=[],
        help="Bilingual web page URL. Can be passed multiple times.",
    )
    parser.add_argument(
        "--disable-hf-streaming",
        action="store_true",
        help="Disable HuggingFace streaming mode (not recommended on low-disk machines).",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    args = _build_arg_parser().parse_args()

    cfg = CrawlerConfig(
        output_dir=Path(args.output_dir),
        bilingual_web_urls=args.web_url,
        github_token=args.github_token,
        hf_streaming=not args.disable_hf_streaming,
    )
    run_crawler(cfg)


if __name__ == "__main__":
    main()
