# ChronosMatch browser front end

This front view is for the ChronosMatch order-matching simulator. It shows the
best bid and ask, spread, midpoint, open quantities, order book, cancellations,
and executed trades. It uses steady sample values; no fake stock-price ticker
or animated price changes are included.

## Preview the screen by itself

Open `ChronosMatch.html` in a browser. This is a browser-only preview, so order
entry, matching, cancellation, and reset work in that tab without Python.

## Connect the front end to the Python project

From PowerShell in the project folder, run:

```powershell
python web_app.py
```

Keep the terminal open and visit <http://127.0.0.1:8000>. The page now reads and
updates the actual Python `ChronosMatch` engine. To stop it, press Ctrl+C in
PowerShell. No additional packages are needed.

The demo is local only. It does not connect to an exchange or send real orders.

## Test the web server

```powershell
python -m unittest -v test_web_app
```
