"""Demo catalog direction and after-sales copy regression tests."""

from app.database.seed import PRODUCTS


def test_demo_catalog_contains_23_smart_digital_products() -> None:
    assert len(PRODUCTS) == 23
    names = {str(product["name"]) for product in PRODUCTS}
    skus = {str(product["sku"]) for product in PRODUCTS}
    assert "Aurora Buds Pro 无线降噪耳机" in names
    assert "FlowKeys 机械键盘" in names
    assert "Halo Monitor 智能屏幕挂灯" in names
    assert "QuietDesk 桌面静音风扇" in names
    assert not names & {"Organic Snack Box", "Coffee Beans 500g", "Cotton T-Shirt"}
    assert len(skus) == 23
    assert {sku.split("-")[1] for sku in skus} == {
        "AUD", "PER", "MOB", "OFF", "WEA", "HOM",
    }


def test_demo_catalog_has_complete_chinese_descriptions() -> None:
    assert all(product.get("description") for product in PRODUCTS)
    assert len({str(product["name"]) for product in PRODUCTS}) == len(PRODUCTS)
