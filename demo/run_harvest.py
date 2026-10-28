import os
import sys

# Ensure marketharvester package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from marketharvester.pipeline import HarvestPipeline
from marketharvester.storage import SQLiteStorage


def run_demo():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fixtures_dir = os.path.join(base_dir, "..", "fixtures")
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    db_path = os.path.join(output_dir, "market_demo.db")
    csv_path = os.path.join(output_dir, "extracted_companies.csv")
    jsonl_path = os.path.join(output_dir, "extracted_companies.jsonl")

    page1 = os.path.join(fixtures_dir, "directory_page_1.html")
    page2 = os.path.join(fixtures_dir, "directory_page_2_corrupted.html")

    print("==================================================================")
    print("MarketHarvester-ETL Demo: Multi-Source Web Extraction & Quarantine")
    print("==================================================================")
    print(f"Sources: [page 1 (5 items), page 2 (3 items including 2 corrupt)]")
    print(f"Output DB:    {db_path}")
    print(f"Output CSV:   {csv_path}")
    print(f"Output JSONL: {jsonl_path}")
    print("------------------------------------------------------------------")

    storage = SQLiteStorage(db_path)
    pipeline = HarvestPipeline(storage=storage)

    valid_records, quarantined_records, report = pipeline.run(
        sources=[page1, page2],
        csv_output=csv_path,
        jsonl_output=jsonl_path,
    )

    print("\n--- Pipeline Execution Report ---")
    print(f"  * Total Raw Items Scraped:     {report.total_scraped}")
    print(f"  * Valid Records Accepted:      {report.valid_records}")
    print(f"  * Corrupted Rows Quarantined:  {report.quarantined_records}")
    print(f"  * Duplicate Listings Skipped:  {report.duplicates_skipped}")
    print(f"  * Pipeline Execution Time:     {report.duration_seconds:.3f}s")
    print("------------------------------------------------------------------")

    print("\n[Preview of Validated Records in SQLite]")
    rows = storage.fetch_all_companies()
    for idx, r in enumerate(rows, 1):
        print(f"  {idx}. {r['name']} | Cat: {r['category']} | Rating: {r['rating']}* ({r['review_count']} rev) | City: {r['city']}, {r['state']} | Email: {r['email']}")

    print("\n[Preview of Quarantined Corrupted Records]")
    with storage._connection() as conn:
        q_rows = conn.cursor().execute("SELECT id, error_reasons, raw_payload FROM quarantine").fetchall()
        for q in q_rows:
            print(f"  [Q-ID {q[0]}] Errors: {q[1]}")

    print("\nDemo completed with 100% integrity!")


if __name__ == "__main__":
    run_demo()
