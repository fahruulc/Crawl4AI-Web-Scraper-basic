from pathlib import Path
import pytest
from crawl4ai import AsyncWebCrawler
from src.config import load_all_targets, load_target_config
from src.extract_css import extract_with_css, load_schema
from src.runner import run_pipeline
from src.storage import Storage
from src.validate import validate_product

FIXTURE_BOOKS = Path("tests/fixtures/books_toscrape.html")
FIXTURE_ECOMMERCE = Path("tests/fixtures/ecommerce_demo.html")

SCHEMA_BOOKS = Path("schemas/books_toscrape.json")
SCHEMA_ECOMMERCE = Path("schemas/ecommerce_demo.json")

TARGET_BOOKS = Path("targets/books_toscrape.yaml")
TARGET_ECOMMERCE = Path("targets/ecommerce_demo.yaml")


def test_m2_config_loader_discovers_both_targets():
    """Verify that both targets are discovered automatically by config loader."""
    targets = load_all_targets("targets")
    target_names = {t.name for t in targets}
    assert "books_toscrape" in target_names
    assert "ecommerce_demo" in target_names
    assert "_template" not in target_names


@pytest.mark.asyncio
async def test_m2_different_layouts_same_schema():
    """
    Kriteria Penerimaan PRD:
    'Dua target dengan layout berbeda menghasilkan tabel dengan skema yang sama.'
    """
    html_books = FIXTURE_BOOKS.read_text(encoding="utf-8")
    schema_books = load_schema(SCHEMA_BOOKS)

    html_ecom = FIXTURE_ECOMMERCE.read_text(encoding="utf-8")
    schema_ecom = load_schema(SCHEMA_ECOMMERCE)

    async with AsyncWebCrawler() as crawler:
        books_items = await extract_with_css(
            crawler=crawler,
            url="https://books.toscrape.com/catalogue/page-1.html",
            schema=schema_books,
            raw_html=html_books,
        )
        ecom_items = await extract_with_css(
            crawler=crawler,
            url="https://webscraper.io/test-sites/e-commerce/static/computers/laptops",
            schema=schema_ecom,
            raw_html=html_ecom,
        )

    assert len(books_items) == 3
    assert len(ecom_items) == 3

    # Validate items from Target 1 (Books)
    books_records = []
    for raw in books_items:
        rec, err = validate_product(raw, target="books_toscrape", source_url="https://books.toscrape.com")
        assert err is None
        books_records.append(rec)

    # Validate items from Target 2 (Ecommerce Laptops)
    ecom_records = []
    for raw in ecom_items:
        rec, err = validate_product(raw, target="ecommerce_demo", source_url="https://webscraper.io")
        assert err is None
        ecom_records.append(rec)

    # Verify both conform to the exact same ProductRecord structure
    assert all(hasattr(r, "name") and hasattr(r, "price") and hasattr(r, "stock") for r in books_records)
    assert all(hasattr(r, "name") and hasattr(r, "price") and hasattr(r, "stock") for r in ecom_records)

    # Verify extracted data for Target 2
    assert ecom_records[0].name == "Asus AsusPro Advanced"
    assert ecom_records[0].price == 295.99
    assert "7 in stock" in ecom_records[0].stock


@pytest.mark.asyncio
async def test_m2_multi_target_database_persistence_and_idempotency(tmp_path):
    """
    Kriteria Penerimaan PRD:
    'Menjalankan dua kali berturut-turut tidak menggandakan data.'
    'Dua target disimpan rapi ke SQLite dengan kunci unik.'
    """
    db_file = tmp_path / "multi_target.db"
    storage = Storage(db_path=db_file)

    # Run target 1
    res1 = await run_pipeline(
        target_name="books_toscrape",
        targets_dir="targets",
        db_path=db_file,
        fixture_path=FIXTURE_BOOKS,
    )
    assert res1["books_toscrape"]["inserted"] == 3

    # Run target 2
    res2 = await run_pipeline(
        target_name="ecommerce_demo",
        targets_dir="targets",
        db_path=db_file,
        fixture_path=FIXTURE_ECOMMERCE,
    )
    assert res2["ecommerce_demo"]["inserted"] == 3

    # Verify both targets coexist in the same database
    assert storage.count_products() == 6
    assert storage.count_products("books_toscrape") == 3
    assert storage.count_products("ecommerce_demo") == 3

    # Re-run target 2 (Idempotency check: 0 inserted, 3 unchanged)
    res2_rerun = await run_pipeline(
        target_name="ecommerce_demo",
        targets_dir="targets",
        db_path=db_file,
        fixture_path=FIXTURE_ECOMMERCE,
    )
    assert res2_rerun["ecommerce_demo"]["inserted"] == 0
    assert res2_rerun["ecommerce_demo"]["unchanged"] == 3
    assert storage.count_products("ecommerce_demo") == 3
    assert storage.count_products() == 6

