import os
from pathlib import Path
import pytest
import pytest_asyncio
from crawl4ai import AsyncWebCrawler
from src.config import TargetConfig, load_all_targets, load_target_config
from src.extract_css import extract_with_css, load_schema
from src.runner import run_pipeline, run_target
from src.storage import Storage
from src.validate import ProductRecord, validate_product

# Silence Crawl4AI cloud notice in tests
os.environ["CRAWL4AI_NO_CLOUD_NOTICE"] = "1"

FIXTURE_HTML_PATH = Path("tests/fixtures/books_toscrape.html")
SCHEMA_PATH = Path("schemas/books_toscrape.json")
TARGET_PATH = Path("targets/books_toscrape.yaml")


def test_config_loader():
    config = load_target_config(TARGET_PATH)
    assert config.name == "books_toscrape"
    assert config.mode == "css"
    assert config.schema_file == "schemas/books_toscrape.json"
    assert len(config.start_urls) == 1

    # Load all targets should include books_toscrape and ignore _template.yaml
    all_targets = load_all_targets("targets")
    names = [t.name for t in all_targets]
    assert "books_toscrape" in names
    assert "target_name" not in names


def test_validation():
    # Valid item
    raw_valid = {
        "name": "  Test Book  ",
        "price": "£25.50",
        "stock": " In stock ",
    }
    record, err = validate_product(raw_valid, target="test", source_url="https://example.com")
    assert err is None
    assert record is not None
    assert record.name == "Test Book"
    assert record.price == 25.50
    assert record.stock == "In stock"

    # Invalid item: empty name
    raw_empty_name = {"name": "   ", "price": "£10.00"}
    record, err = validate_product(raw_empty_name, target="test", source_url="https://example.com")
    assert record is None
    assert "Product name cannot be empty" in err

    # Invalid item: bad price
    raw_bad_price = {"name": "Valid Book", "price": "Not a number"}
    record, err = validate_product(raw_bad_price, target="test", source_url="https://example.com")
    assert record is None
    assert "Unable to parse price" in err


def test_storage_idempotency_and_history(tmp_path):
    db_file = tmp_path / "test.db"
    storage = Storage(db_path=db_file)

    rec1 = ProductRecord(
        target="books",
        source_url="https://example.com/item1",
        name="Book A",
        price=10.0,
        stock="In stock",
    )

    # 1. First save -> inserted
    res1 = storage.save_product(rec1)
    assert res1["action"] == "inserted"
    assert storage.count_products("books") == 1
    history1 = storage.get_price_history(res1["id"])
    assert len(history1) == 1
    assert history1[0]["price"] == 10.0

    # 2. Second save with identical data -> unchanged (idempotent, no duplicates)
    res2 = storage.save_product(rec1)
    assert res2["action"] == "unchanged"
    assert storage.count_products("books") == 1
    assert len(storage.get_price_history(res1["id"])) == 1

    # 3. Third save with changed price -> updated and history recorded
    rec1_updated = ProductRecord(
        target="books",
        source_url="https://example.com/item1",
        name="Book A",
        price=12.5,
        stock="Out of stock",
    )
    res3 = storage.save_product(rec1_updated)
    assert res3["action"] == "updated"
    assert res3["old_price"] == 10.0
    assert res3["new_price"] == 12.5
    assert storage.count_products("books") == 1
    history3 = storage.get_price_history(res1["id"])
    assert len(history3) == 2
    assert history3[1]["price"] == 12.5


@pytest.mark.asyncio
async def test_extract_css_with_offline_fixture():
    html_content = FIXTURE_HTML_PATH.read_text(encoding="utf-8")
    schema = load_schema(SCHEMA_PATH)

    async with AsyncWebCrawler() as crawler:
        items = await extract_with_css(
            crawler=crawler,
            url="https://books.toscrape.com/catalogue/page-1.html",
            schema=schema,
            raw_html=html_content,
        )

    assert len(items) == 3
    assert items[0]["name"] == "A Light in the Attic"
    assert items[0]["price"] == "£51.77"
    assert "In stock" in items[0]["stock"]

    assert items[1]["name"] == "Tipping the Velvet"
    assert items[1]["price"] == "£53.74"

    assert items[2]["name"] == "Soumission"
    assert items[2]["price"] == "£50.10"


@pytest.mark.asyncio
async def test_full_pipeline_offline_run(tmp_path):
    db_file = tmp_path / "pipeline.db"

    # Run 1: initial run
    results1 = await run_pipeline(
        target_name="books_toscrape",
        targets_dir="targets",
        db_path=db_file,
        fixture_path=FIXTURE_HTML_PATH,
    )
    assert "books_toscrape" in results1
    stats1 = results1["books_toscrape"]
    assert stats1["items_extracted"] == 3
    assert stats1["items_valid"] == 3
    assert stats1["inserted"] == 3
    assert stats1["unchanged"] == 0

    storage = Storage(db_path=db_file)
    assert storage.count_products("books_toscrape") == 3

    # Run 2: idempotent re-run (no duplicate data)
    results2 = await run_pipeline(
        target_name="books_toscrape",
        targets_dir="targets",
        db_path=db_file,
        fixture_path=FIXTURE_HTML_PATH,
    )
    stats2 = results2["books_toscrape"]
    assert stats2["inserted"] == 0
    assert stats2["unchanged"] == 3
    assert storage.count_products("books_toscrape") == 3


@pytest.mark.asyncio
async def test_fault_tolerance_one_target_failing(tmp_path):
    db_file = tmp_path / "fault_test.db"
    storage = Storage(db_path=db_file)

    bad_target = TargetConfig(
        name="bad_target",
        start_urls=["https://example.com/bad"],
        mode="css",
        schema_file="schemas/non_existent_schema.json",
    )
    good_target = load_target_config(TARGET_PATH)
    fixture_content = FIXTURE_HTML_PATH.read_text(encoding="utf-8")

    async with AsyncWebCrawler() as crawler:
        # Run bad target - errors are caught and logged, returning 0 valid items
        bad_stats = await run_target(bad_target, storage, crawler, fixture_content=fixture_content)
        assert bad_stats["items_valid"] == 0

        # Good target runs successfully even after bad target failed
        good_stats = await run_target(good_target, storage, crawler, fixture_content=fixture_content)
        assert good_stats["items_valid"] == 3
        assert good_stats["inserted"] == 3
