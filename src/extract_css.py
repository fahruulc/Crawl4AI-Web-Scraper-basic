from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


def load_schema(schema_file_path: str | Path) -> Dict[str, Any]:
    path = Path(schema_file_path)
    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def extract_with_css(
    crawler: AsyncWebCrawler,
    url: str,
    schema: Dict[str, Any] | str | Path,
    raw_html: Optional[str] = None,
    scroll_full_page: bool = False,
) -> List[Dict[str, Any]]:
    """
    Extract structured data using Crawl4AI's JsonCssExtractionStrategy.
    If raw_html is provided, extracts offline using raw: prefix.
    """
    if isinstance(schema, (str, Path)):
        schema_dict = load_schema(schema)
    else:
        schema_dict = schema

    strategy = JsonCssExtractionStrategy(schema=schema_dict)
    run_config = CrawlerRunConfig(
        extraction_strategy=strategy,
        cache_mode=CacheMode.BYPASS,
        scan_full_page=scroll_full_page,
    )

    crawl_target = f"raw:{raw_html}" if raw_html is not None else url
    result = await crawler.arun(url=crawl_target, config=run_config)

    if not result.success:
        raise RuntimeError(f"Crawl4AI extraction failed for {url}: {result.error_message}")

    extracted_raw = result.extracted_content or "[]"
    try:
        data = json.loads(extracted_raw)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to decode extracted JSON: {exc}. Content was: {extracted_raw[:200]}")

