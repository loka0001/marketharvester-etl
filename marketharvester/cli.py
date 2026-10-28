import os
import sys
import argparse
from marketharvester.pipeline import HarvestPipeline
from marketharvester.storage import SQLiteStorage


def main():
    parser = argparse.ArgumentParser(
        description="MarketHarvester-ETL: Resilient Multi-Source Web Extraction & Schema Validation Pipeline"
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="One or more HTML file paths or HTTP(S) URLs to harvest"
    )
    parser.add_argument(
        "--db",
        default="output/harvest.db",
        help="Path to SQLite database output (default: output/harvest.db)"
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="Optional path to export validated records to CSV"
    )
    parser.add_argument(
        "--jsonl",
        default=None,
        help="Optional path to export validated records to JSON Lines"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Max retries for network fetches (default: 3)"
    )

    args = parser.parse_args()

    print("==================================================================")
    print("MarketHarvester-ETL: Enterprise Extraction & Validation Pipeline")
    print("==================================================================")
    print(f"Sources to harvest: {len(args.sources)}")
    print(f"Target Database:    {args.db}")
    if args.csv:
        print(f"Target CSV:         {args.csv}")
    if args.jsonl:
        print(f"Target JSONL:       {args.jsonl}")
    print("------------------------------------------------------------------")

    storage = SQLiteStorage(args.db)
    pipeline = HarvestPipeline(storage=storage)

    valid, quarantined, report = pipeline.run(
        sources=args.sources,
        jsonl_output=args.jsonl,
        csv_output=args.csv,
    )

    print("\n--- Pipeline Execution Summary ---")
    print(f"  * Total Raw Scraped:     {report.total_scraped}")
    print(f"  * Valid Schema Records:  {report.valid_records}")
    print(f"  * Quarantined (Corrupt): {report.quarantined_records}")
    print(f"  * Duplicates Deduplicated:{report.duplicates_skipped}")
    print(f"  * Pipeline Runtime:      {report.duration_seconds}s")
    print(f"  * Database Total Stored: {storage.count_companies()}")
    print("==================================================================")


if __name__ == "__main__":
    main()
