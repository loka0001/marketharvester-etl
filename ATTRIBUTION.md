# Attribution & Origin

**Project Name:** MarketHarvester-ETL  
**Primary Author:** Malek Mesbah (<maleksobhy2004@gmail.com>)  
**License:** MIT License  
**Originality:** Original Work  

## Origin & Context
MarketHarvester-ETL was engineered as an enterprise-grade solution to address common industrial data extraction challenges observed in Upwork market demand signals:
- Fragile web scrapers that crash on schema mutations or network transient errors.
- Absence of validation contracts, resulting in corrupted data entering production data lakes.
- Lack of graceful quarantine mechanisms for malformed records.
- Inefficient or absent deduplication logic across multi-page crawls.

This package provides a zero-leakage, type-safe extraction and ingestion pipeline using Pydantic v2 schemas, automated HTTP exponential backoff with jitter, SQLite indexed upserts, and an isolated quarantine audit table.
