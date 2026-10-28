import os
import json
import csv
import sqlite3
from contextlib import contextmanager
from typing import List, Optional, Generator
from marketharvester.models import CompanyRecord, QuarantineRecord, HarvestReport


class SQLiteStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                company_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                rating REAL,
                review_count INTEGER,
                email TEXT,
                phone TEXT,
                website TEXT,
                street TEXT,
                city TEXT NOT NULL,
                state TEXT,
                postal_code TEXT,
                country TEXT,
                source_url TEXT,
                extracted_at TEXT NOT NULL,
                hash_fingerprint TEXT UNIQUE NOT NULL
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_category ON companies(category);
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_city ON companies(city);
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_fingerprint ON companies(hash_fingerprint);
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS quarantine (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                error_reasons TEXT,
                raw_payload TEXT,
                quarantined_at TEXT NOT NULL
            );
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS harvest_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_scraped INTEGER,
                valid_records INTEGER,
                quarantined_records INTEGER,
                duplicates_skipped INTEGER,
                duration_seconds REAL,
                completed_at TEXT NOT NULL
            );
            """)
            conn.commit()

    def upsert_company(self, record: CompanyRecord) -> bool:
        """
        Inserts or updates a company record. Returns True if inserted, False if updated.
        """
        sql = """
        INSERT INTO companies (
            company_id, name, category, rating, review_count,
            email, phone, website, street, city, state, postal_code,
            country, source_url, extracted_at, hash_fingerprint
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(hash_fingerprint) DO UPDATE SET
            rating = excluded.rating,
            review_count = excluded.review_count,
            email = COALESCE(excluded.email, companies.email),
            phone = COALESCE(excluded.phone, companies.phone),
            website = COALESCE(excluded.website, companies.website),
            extracted_at = excluded.extracted_at;
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                record.company_id,
                record.name,
                record.category,
                record.rating,
                record.review_count,
                record.contact.email,
                record.contact.phone,
                record.contact.website,
                record.address.street,
                record.address.city,
                record.address.state,
                record.address.postal_code,
                record.address.country,
                record.source_url,
                record.extracted_at,
                record.hash_fingerprint,
            ))
            conn.commit()
            return cursor.rowcount > 0

    def insert_quarantine(self, quarantine: QuarantineRecord):
        sql = """
        INSERT INTO quarantine (source, error_reasons, raw_payload, quarantined_at)
        VALUES (?, ?, ?, ?);
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                quarantine.source,
                json.dumps(quarantine.error_reasons),
                json.dumps(quarantine.raw_data),
                quarantine.quarantined_at,
            ))
            conn.commit()

    def record_run(self, report: HarvestReport):
        sql = """
        INSERT INTO harvest_runs (
            total_scraped, valid_records, quarantined_records,
            duplicates_skipped, duration_seconds, completed_at
        ) VALUES (?, ?, ?, ?, ?, datetime('now'));
        """
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (
                report.total_scraped,
                report.valid_records,
                report.quarantined_records,
                report.duplicates_skipped,
                report.duration_seconds,
            ))
            conn.commit()

    def count_companies(self) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM companies")
            return cursor.fetchone()[0]

    def count_quarantined(self) -> int:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM quarantine")
            return cursor.fetchone()[0]

    def fetch_all_companies(self) -> List[sqlite3.Row]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM companies ORDER BY name ASC")
            return cursor.fetchall()


def export_jsonl(records: List[CompanyRecord], filepath: str):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        for r in records:
            f.write(r.model_dump_json() + "\n")


def export_csv(records: List[CompanyRecord], filepath: str):
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    fieldnames = [
        "company_id", "name", "category", "rating", "review_count",
        "email", "phone", "website", "street", "city", "state", "postal_code",
        "country", "source_url", "extracted_at", "hash_fingerprint"
    ]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                "company_id": r.company_id,
                "name": r.name,
                "category": r.category,
                "rating": r.rating,
                "review_count": r.review_count,
                "email": r.contact.email,
                "phone": r.contact.phone,
                "website": r.contact.website,
                "street": r.address.street,
                "city": r.address.city,
                "state": r.address.state,
                "postal_code": r.address.postal_code,
                "country": r.address.country,
                "source_url": r.source_url,
                "extracted_at": r.extracted_at,
                "hash_fingerprint": r.hash_fingerprint,
            })
