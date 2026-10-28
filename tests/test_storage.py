import os
import tempfile
from marketharvester.models import CompanyRecord, QuarantineRecord, ContactInfo, Address, HarvestReport
from marketharvester.storage import SQLiteStorage, export_jsonl, export_csv


def test_sqlite_storage_upsert_and_quarantine():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        storage = SQLiteStorage(db_path)

        rec1 = CompanyRecord(
            name="Alpha Corp",
            category="Consulting",
            rating=4.5,
            review_count=10,
            contact=ContactInfo(email="info@alpha.com", phone="5125551234"),
            address=Address(city="Houston")
        )

        inserted = storage.upsert_company(rec1)
        assert inserted is True
        assert storage.count_companies() == 1

        # Re-upsert with updated rating
        rec1_updated = CompanyRecord(
            name="Alpha Corp",
            category="Consulting",
            rating=4.9,
            review_count=15,
            contact=ContactInfo(email="info@alpha.com", phone="5125551234"),
            address=Address(city="Houston")
        )
        storage.upsert_company(rec1_updated)
        assert storage.count_companies() == 1  # No duplicate row created

        # Test quarantine insert
        quarantine = QuarantineRecord(
            raw_data={"name": "Bad Co"},
            error_reasons=["Missing city"],
            source="test_src"
        )
        storage.insert_quarantine(quarantine)
        assert storage.count_quarantined() == 1

        # Test run report record
        storage.record_run(HarvestReport(total_scraped=2, valid_records=1, quarantined_records=1))


def test_export_jsonl_and_csv():
    with tempfile.TemporaryDirectory() as tmpdir:
        jsonl_path = os.path.join(tmpdir, "out.jsonl")
        csv_path = os.path.join(tmpdir, "out.csv")

        records = [
            CompanyRecord(
                name="Beta LLC",
                contact=ContactInfo(email="hello@beta.com"),
                address=Address(city="Dallas")
            )
        ]

        export_jsonl(records, jsonl_path)
        assert os.path.exists(jsonl_path)
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            assert "Beta LLC" in lines[0]

        export_csv(records, csv_path)
        assert os.path.exists(csv_path)
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Beta LLC" in content
            assert "Dallas" in content
