import os
import tempfile
from marketharvester.pipeline import HarvestPipeline
from marketharvester.storage import SQLiteStorage


def test_harvest_pipeline_end_to_end():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    page1 = os.path.join(fixtures_dir, "directory_page_1.html")
    page2 = os.path.join(fixtures_dir, "directory_page_2_corrupted.html")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "pipeline_test.db")
        csv_path = os.path.join(tmpdir, "pipeline_test.csv")
        storage = SQLiteStorage(db_path)

        pipeline = HarvestPipeline(storage=storage)
        valid, quarantined, report = pipeline.run(
            sources=[page1, page2],
            csv_output=csv_path
        )

        # Page 1 had 5 items (4 unique valid + 1 duplicate)
        # Page 2 had 3 items (1 valid + 2 corrupt)
        # Total scraped = 8
        assert report.total_scraped == 8
        # Unique valid: 4 from page 1 + 1 from page 2 = 5
        assert report.valid_records == 5
        assert len(valid) == 5
        # Duplicates skipped = 1
        assert report.duplicates_skipped == 1
        # Quarantined = 2
        assert report.quarantined_records == 2
        assert len(quarantined) == 2

        # Verify DB counts
        assert storage.count_companies() == 5
        assert storage.count_quarantined() == 2

        # Verify CSV was written
        assert os.path.exists(csv_path)
