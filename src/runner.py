from __future__ import annotations
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from crawl4ai import AsyncWebCrawler
from src.config import TargetConfig, load_all_targets, load_target_config
from src.extract_css import extract_with_css
from src.storage import Storage
from src.validate import validate_generic, validate_product

# Silence optional cloud notice if desired
os.environ.setdefault("CRAWL4AI_NO_CLOUD_NOTICE", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scraper.runner")


async def run_target(
    target: TargetConfig,
    storage: Storage,
    crawler: AsyncWebCrawler,
    fixture_content: Optional[str] = None,
) -> Dict[str, int]:
    """
    Run scraping for a single target.
    Returns summary statistics for items processed.
    """
    logger.info(f"--- Starting target: {target.name} (mode: {target.mode}) ---")
    stats = {
        "urls_processed": 0,
        "items_extracted": 0,
        "items_valid": 0,
        "items_invalid": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
    }

    if target.mode != "css":
        raise NotImplementedError(
            f"Mode '{target.mode}' is not yet implemented (scheduled for M3). Use mode 'css'."
        )

    for i, url in enumerate(target.start_urls):
        if i >= target.max_pages:
            logger.info(f"Target {target.name}: Reached max_pages ({target.max_pages}). Stopping.")
            break

        logger.info(f"Processing URL [{i+1}/{len(target.start_urls)}]: {url}")
        try:
            items = await extract_with_css(
                crawler=crawler,
                url=url,
                schema=target.schema_file,
                raw_html=fixture_content,
                scroll_full_page=target.scroll_full_page,
            )
            stats["urls_processed"] += 1
            stats["items_extracted"] += len(items)
            logger.info(f"Extracted {len(items)} raw items from {url}")

            for raw_item in items:
                # Check if item conforms to standard ProductRecord (has 'name' and 'price')
                if "name" in raw_item and "price" in raw_item:
                    record, err = validate_product(raw_item, target=target.name, source_url=url)
                    if record is None:
                        stats["items_invalid"] += 1
                        logger.warning(f"Invalid record rejected: {raw_item} | Reason: {err}")
                        continue

                    stats["items_valid"] += 1
                    res = storage.save_product(record)
                    action = res.get("action")
                    if action == "inserted":
                        stats["inserted"] += 1
                    elif action == "updated":
                        stats["updated"] += 1
                        logger.info(f"Price/stock updated for '{record.name}': {res}")
                    elif action == "unchanged":
                        stats["unchanged"] += 1
                else:
                    # Dynamic / generic schema for custom target (e.g. jobs, articles, etc.)
                    clean_item, err = validate_generic(raw_item, target=target.name, source_url=url)
                    if clean_item is None:
                        stats["items_invalid"] += 1
                        logger.warning(f"Invalid generic record rejected: {raw_item} | Reason: {err}")
                        continue

                    stats["items_valid"] += 1
                    res = storage.save_generic(
                        target=target.name,
                        source_url=url,
                        data=clean_item,
                        table_name=target.name,
                    )
                    action = res.get("action")
                    if action == "inserted":
                        stats["inserted"] += 1
                    elif action == "updated":
                        stats["updated"] += 1
                        logger.info(f"Dynamic record updated in '{target.name}': {res}")
                    elif action == "unchanged":
                        stats["unchanged"] += 1

        except Exception as exc:
            logger.error(f"Error scraping URL {url} on target {target.name}: {exc}", exc_info=True)

        # Rate limiting between URLs if not offline fixture
        if fixture_content is None and i < len(target.start_urls) - 1:
            await asyncio.sleep(target.rate_limit_seconds)

    logger.info(
        f"Completed target '{target.name}': "
        f"{stats['items_valid']} valid ({stats['inserted']} inserted, {stats['updated']} updated, "
        f"{stats['unchanged']} unchanged), {stats['items_invalid']} invalid."
    )
    return stats


async def run_pipeline(
    target_name: Optional[str] = None,
    targets_dir: str | Path = "targets",
    db_path: str | Path = "data/scraper.db",
    fixture_path: Optional[str | Path] = None,
) -> Dict[str, Dict[str, int]]:
    storage = Storage(db_path=db_path)

    fixture_content = None
    if fixture_path:
        fixture_file = Path(fixture_path)
        if fixture_file.exists():
            fixture_content = fixture_file.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"Fixture file not found: {fixture_path}")

    # Determine targets to run
    if target_name:
        target_file = Path(targets_dir) / f"{target_name}.yaml"
        if not target_file.exists():
            raise FileNotFoundError(f"Target config file not found: {target_file}")
        targets = [load_target_config(target_file)]
    else:
        targets = load_all_targets(targets_dir)

    if not targets:
        logger.warning(f"No target configurations found in {targets_dir}")
        return {}

    overall_results: Dict[str, Dict[str, int]] = {}

    async with AsyncWebCrawler() as crawler:
        for tgt in targets:
            try:
                stats = await run_target(
                    target=tgt,
                    storage=storage,
                    crawler=crawler,
                    fixture_content=fixture_content,
                )
                overall_results[tgt.name] = stats
            except Exception as tgt_err:
                # One target failing must not stop other targets
                logger.error(f"Target '{tgt.name}' failed with error: {tgt_err}", exc_info=True)
                overall_results[tgt.name] = {"error": 1}

    return overall_results


def main() -> None:
    parser = argparse.ArgumentParser(description="Config-Driven Web Scraper with Crawl4AI")
    parser.add_argument("--target", "-t", type=str, help="Specific target name (without .yaml)")
    parser.add_argument("--targets-dir", type=str, default="targets", help="Targets directory")
    parser.add_argument("--db", type=str, default="data/scraper.db", help="Path to SQLite database")
    parser.add_argument("--fixture", "-f", type=str, help="Path to offline HTML fixture for testing")
    args = parser.parse_args()

    results = asyncio.run(
        run_pipeline(
            target_name=args.target,
            targets_dir=args.targets_dir,
            db_path=args.db,
            fixture_path=args.fixture,
        )
    )
    print("\n=== Scraping Execution Summary ===")
    for tgt_name, res in results.items():
        print(f"Target [{tgt_name}]: {res}")


if __name__ == "__main__":
    main()

