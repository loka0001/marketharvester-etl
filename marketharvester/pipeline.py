import os
import time
import logging
from typing import List, Optional, Tuple, Dict, Any
from pydantic import ValidationError

from marketharvester.models import CompanyRecord, QuarantineRecord, HarvestReport
from marketharvester.client import ResilientClient
from marketharvester.parsers import extract_directory_listings
from marketharvester.storage import SQLiteStorage, export_jsonl, export_csv

logger = logging.getLogger("marketharvester.pipeline")


class HarvestPipeline:
    def __init__(
        self,
        storage: Optional[SQLiteStorage] = None,
        client: Optional[ResilientClient] = None,
    ):
        self.storage = storage
        self.client = client or ResilientClient()
        self.seen_fingerprints = set()

    def load_html(self, source: str) -> str:
        """Loads HTML content from either a local file path or a remote URL."""
        if os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                return f.read()
        elif source.startswith("http://") or source.startswith("https://"):
            return self.client.get_html(source)
        else:
            raise ValueError(f"Source must be an existing file path or an HTTP(S) URL: {source}")

    def process_raw_item(self, item: Dict[str, Any], source: str) -> Tuple[Optional[CompanyRecord], Optional[QuarantineRecord]]:
        """Validates a single raw dictionary against CompanyRecord schema."""
        try:
            record = CompanyRecord(**item)
            return record, None
        except ValidationError as err:
            reasons = [f"{e['loc']}: {e['msg']}" for e in err.errors()]
            quarantine = QuarantineRecord(
                raw_data=item,
                error_reasons=reasons,
                source=source,
            )
            return None, quarantine
        except Exception as exc:
            quarantine = QuarantineRecord(
                raw_data=item,
                error_reasons=[str(exc)],
                source=source,
            )
            return None, quarantine

    def run(
        self,
        sources: List[str],
        jsonl_output: Optional[str] = None,
        csv_output: Optional[str] = None,
    ) -> Tuple[List[CompanyRecord], List[QuarantineRecord], HarvestReport]:
        start_time = time.time()
        valid_records: List[CompanyRecord] = []
        quarantine_records: List[QuarantineRecord] = []
        duplicates_skipped = 0
        total_scraped = 0

        for src in sources:
            try:
                html = self.load_html(src)
                raw_items = extract_directory_listings(html, source_url=src)
                total_scraped += len(raw_items)

                for item in raw_items:
                    valid_rec, quarantine_rec = self.process_raw_item(item, source=src)
                    
                    if quarantine_rec:
                        quarantine_records.append(quarantine_rec)
                        if self.storage:
                            self.storage.insert_quarantine(quarantine_rec)
                    elif valid_rec:
                        # In-memory deduplication check
                        if valid_rec.hash_fingerprint in self.seen_fingerprints:
                            duplicates_skipped += 1
                        else:
                            self.seen_fingerprints.add(valid_rec.hash_fingerprint)
                            valid_records.append(valid_rec)
                            if self.storage:
                                self.storage.upsert_company(valid_rec)

            except Exception as e:
                logger.error(f"Error processing source {src}: {e}")
                # Record page-level failure into quarantine
                q = QuarantineRecord(
                    raw_data={"source_path": src},
                    error_reasons=[f"Source processing failure: {str(e)}"],
                    source=src,
                )
                quarantine_records.append(q)
                if self.storage:
                    self.storage.insert_quarantine(q)

        duration = time.time() - start_time
        report = HarvestReport(
            total_scraped=total_scraped,
            valid_records=len(valid_records),
            quarantined_records=len(quarantine_records),
            duplicates_skipped=duplicates_skipped,
            duration_seconds=round(duration, 3),
        )

        if self.storage:
            self.storage.record_run(report)

        if jsonl_output:
            export_jsonl(valid_records, jsonl_output)

        if csv_output:
            export_csv(valid_records, csv_output)

        return valid_records, quarantine_records, report
