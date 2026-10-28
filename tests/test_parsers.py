import os
from marketharvester.parsers import extract_directory_listings


def test_parse_directory_page_1():
    fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "directory_page_1.html")
    with open(fixture_path, "r", encoding="utf-8") as f:
        html = f.read()

    items = extract_directory_listings(html, source_url="file://page1.html")
    assert len(items) == 5

    names = [it["name"] for it in items]
    assert "Apex Plumbing & Heating" in names
    assert "Quantum Dental Studio" in names
    assert "Solstice Solar Systems" in names

    first = items[0]
    assert first["rating"] == 4.8
    assert first["review_count"] == 142
    assert first["contact"]["phone"] == "+1-512-555-0199"
    assert first["contact"]["email"] == "service@apexplumb.com"
    assert first["address"]["city"] == "Austin"
    assert first["address"]["state"] == "TX"


def test_parse_empty_html():
    items = extract_directory_listings("<html><body><p>No listings</p></body></html>")
    assert items == []
