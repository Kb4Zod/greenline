# 0003 — Bank data ingestion: manual CSV only (for now)

**Date:** 2026-06-12

## Decided

The MVP ingests bank history via **manual CSV import only.** No Plaid, no Open Banking, no direct bank API. The parser sits behind a format-agnostic interface so OFX/QFX/QBO can be added later without rework.

## Why

- **Privacy.** A bank API means a third party in the loop and credentials flying around. That breaks the local-first, public-repo posture. Manual download keeps everything on Hugh's machine.
- **Fits the cadence.** The whole product is a weekly ritual: download statement, import, glance. Manual import *is* the loop, not friction around it.
- **Hugh wasn't sure which formats his bank exports.** Rather than guess at OFX/QFX, start with CSV (universal) and add formats once we see real exports. Don't build parsers for formats we haven't confirmed exist.

## Open thread

We still need a **real sample CSV** (headers + a few scrubbed rows) from Hugh's actual bank before the Spec, because the column layout drives the entire import + dedup design. Flagged, not resolved.

## Status

Active. Format support is intentionally extensible.
