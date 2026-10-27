import io
import json
from contextlib import redirect_stdout
from run_simulation import main, run_simulation
import tempfile
import unittest
from pathlib import Path

from run_simulation import run_simulation
from trade_store import SQLiteTradeStore


class TestSimulationTradeStore(unittest.TestCase):
    def test_cli_database_option_saves_trades(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"
            output = io.StringIO()

            with redirect_stdout(output):
                main([
                    "--count", "100",
                    "--seed", "7",
                    "--database", str(path),
                    "--json",
                ])

            summary = json.loads(output.getvalue())

            with SQLiteTradeStore(path) as store:
                self.assertEqual(
                    len(store.get_trades()),
                    summary["trade_count"],
                )
    def test_simulation_saves_trades_to_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.db"

            with SQLiteTradeStore(path) as store:
                summary = run_simulation(
                    count=100,
                    seed=7,
                    trade_store=store,
                )
                saved_trades = store.get_trades()

                self.assertEqual(
                    len(saved_trades),
                    summary["trade_count"],
                )
                self.assertEqual(
                    sum(trade["quantity"] for trade in saved_trades),
                    summary["traded_quantity"],
                )


if __name__ == "__main__":
    unittest.main()
