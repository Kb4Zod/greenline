# 0002 — Local-first stack: FastAPI + SQLite + React

**Date:** 2026-06-12

## Decided

Greenline runs locally: a **FastAPI** backend, **SQLite** for storage, a **React (Vite) + Tailwind** frontend, opened in the browser at `localhost`. Optionally Dockerized.

## Why

- **Local-first** is non-negotiable for a finance app holding real bank data (see 0001). No cloud, no telemetry.
- SQLite = a single local file. Trivial to back up, no server to run, fits one-user scope.
- FastAPI is the known, comfortable backend (same shape as the coffee-tracker precedent).

## The tension I flagged

My default for Hugh is PowerShell. I deliberately steered *away* from it here. The UX bar he set — "user-friendly, easily scannable, almost addictively designed" — wants a real web frontend with proper state and interaction. PowerShell can't deliver that habit-forming check-in screen. So: Python/web for this one, even though it breaks the usual PS pattern.

Considered but rejected for the MVP: a desktop-wrapped app (Tauri/Electron). It's a nicer "native window" feel, but it adds packaging complexity for no MVP value. Browser-at-localhost is simpler and we can wrap later if it earns it.

## Status

Active.
