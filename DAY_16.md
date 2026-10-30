# Day 16 — ChronosMatch
Date: 2026-10-29

## What I worked on
I improved how the project saves and reports completed trades using SQLite. I added trade searches by order ID, per-order summaries with trade count, total quantity, and VWAP, and a limit for report results. I also added database indexes to help trade searches and updated the README with usage examples.

I added tests for report filters, invalid options, and simulations with no trades.

## Testing
The latest database reopen test still needs to be run successfully before I count it as complete.

## Next
I will verify the SQLite simulation tests and push the change after they pass.