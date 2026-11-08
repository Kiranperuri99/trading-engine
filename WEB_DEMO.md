# ChronosMatch multi-stock browser demo

The local browser screen presents a searchable watchlist, a continuously scrolling red/green ticker, a selected-symbol chart, a limit-order ticket, and per-symbol order books and trade history. The ticker animates small simulated price pulses around the sample prices; it is not a live market feed. Each supported symbol has its own in-memory `ChronosMatch` instance, so orders for one symbol never change another symbol's book.

The selected-symbol chart, displayed market snapshot, and daily percentage changes are fixed illustrative values. The scrolling ticker adds simulated pulse changes for visual demonstration. None are live quotes. Orders run only through the local Python matching engine; the page does not connect to a broker or exchange and does not manage holdings, cash, or real trades.

## Run on Windows

Open PowerShell in the project folder and run:

```powershell
python -m unittest -v test_web_app
python .\web_app.py
```

Keep that terminal open, then visit <http://127.0.0.1:8000> in a browser. Press `Ctrl+C` in PowerShell to stop the server.

To choose another local port, use `python .\web_app.py --port 8080` and open <http://127.0.0.1:8080>.

## Browser-only preview

The `web\index.html` file can also be opened directly. If the local server is unavailable, the controls use an in-browser demonstration book. Start `web_app.py` to send orders to the real Python `ChronosMatch` engine instead.

## Controls

- Search or select a symbol in the watchlist; each symbol shows its own independent book.
- Choose Buy or Sell, enter a positive whole quantity and a limit price, then submit. A crossing order matches immediately; any remaining quantity rests in the book.
- Cancel a resting order from the activity table.
- Reset the selected symbol's book. Other symbol books are unchanged. The reset endpoint can reset every book when no symbol is supplied.
- Use the header navigation to jump to the order book and activity panels. Select 1D, 1W, 1M, or 1Y to redraw the deterministic illustrative chart.

## Tests

```powershell
python -m unittest -v test_web_app
```
