from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from chassis.policy import PolicyEngine
from chassis.goal import Goal, Tier
from domains.buyer.landed_cost import format_rank_table, get_spec, rank
from domains.buyer.negotiate import RESERVATION_OFF, reservation_unit
from domains.buyer.po import po_total, write_po
from domains.buyer.__main__ import main


BUYER_PY = Path(__file__).resolve().parents[1] / "domains" / "buyer"


class RankTests(unittest.TestCase):
    def test_box24_winner_is_v05(self) -> None:
        spec = get_spec("BOX-24")
        quotes = rank(spec)
        self.assertTrue(quotes)
        self.assertEqual(quotes[0].vendor_id, "V-05")
        self.assertAlmostEqual(quotes[0].landed, 3610.00, places=2)
        ids = [q.vendor_id for q in quotes]
        self.assertNotIn("V-03", ids)
        table = format_rank_table(spec, quotes)
        self.assertIn("ship", table)
        self.assertIn("penalty", table)
        self.assertIn("landed", table)
        self.assertIn("V-05", table)

    def test_box24_fast_winner_is_v04(self) -> None:
        quotes = rank(get_spec("BOX-24-FAST"))
        self.assertEqual([q.vendor_id for q in quotes], ["V-04"])

    def test_wrap_fast_only_v09(self) -> None:
        quotes = rank(get_spec("WRAP-FAST"))
        self.assertEqual([q.vendor_id for q in quotes], ["V-09"])


class NegotiateTests(unittest.TestCase):
    def test_reservation_is_ten_percent_and_above_floor(self) -> None:
        quote = rank(get_spec("BOX-24"))[0]
        res = reservation_unit(quote.unit_price, quote.floor)
        self.assertAlmostEqual(res.unit, quote.unit_price * (1.0 - RESERVATION_OFF), places=6)
        self.assertGreaterEqual(res.unit, quote.floor)
        self.assertTrue(res.meets_ten_percent)

    def test_floor_blocks_going_under_cost(self) -> None:
        res = reservation_unit(2.00, 1.95)
        self.assertAlmostEqual(res.unit, 1.95, places=6)
        self.assertFalse(res.meets_ten_percent)
        self.assertTrue(res.walk_if_not_met)


class PoTests(unittest.TestCase):
    def test_write_po_without_approval_creates_no_file(self) -> None:
        spec = get_spec("BOX-24")
        quote = rank(spec)[0]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_po(spec, quote, approved=False, dest=dest, cap_usd=None)
            self.assertIsNone(path)
            self.assertEqual(list(dest.glob("po_*.md")), [])

    def test_write_po_approved_uses_reservation_total(self) -> None:
        spec = get_spec("BOX-24")
        quote = rank(spec)[0]
        total = po_total(quote)
        self.assertAlmostEqual(total, 1.512 * 2000 + 250.0, places=2)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_po(spec, quote, approved=True, dest=dest, cap_usd=None)
            self.assertIsNotNone(path)
            assert path is not None
            body = path.read_text(encoding="utf-8")
            self.assertIn("Reservation unit: $1.5120", body)
            self.assertIn("Not sent", body)
            self.assertIn(f"Total: ${total:.2f}", body)

    def test_cap_below_total_writes_nothing(self) -> None:
        spec = get_spec("BOX-24")
        quote = rank(spec)[0]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            path = write_po(spec, quote, approved=True, dest=dest, cap_usd=1.0)
            self.assertIsNone(path)
            self.assertEqual(list(dest.glob("po_*.md")), [])


class PolicyAndSourceTests(unittest.TestCase):
    def test_write_po_without_approval_escalates(self) -> None:
        engine = PolicyEngine()
        goal = Goal(id="p1", domain="buyer", text="po", tier=Tier.ACT_UNDER_CAP)
        d = engine.check(goal, "write_po")
        self.assertEqual(d.verdict, "ESCALATE")

    def test_no_mailer_or_send_callable(self) -> None:
        text = "\n".join(p.read_text(encoding="utf-8") for p in BUYER_PY.glob("*.py"))
        self.assertNotIn("smtplib", text)
        self.assertNotIn("email.mime", text)
        self.assertNotRegex(text, r"\bsend_po\s*\(")


class CliTests(unittest.TestCase):
    def test_rank_box24_prints_table(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            code = main(["rank", "--spec", "BOX-24"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("V-05", out)
        self.assertIn("landed", out)
        self.assertIn("penalty", out)

    def test_draft_prints_reservation_and_not_sent(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.stdout", buf), patch("domains.buyer.__main__.OUT", Path(tmp)):
                code = main(["draft", "--spec", "BOX-24"])
        self.assertEqual(code, 0)
        out = buf.getvalue()
        self.assertIn("1.512", out)
        self.assertIn("not sent", out.lower())
        self.assertIn("10%", out)

    def test_cli_po_without_approve_escalates(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.buyer.__main__.OUT", dest):
                code = main(["po", "--spec", "BOX-24"])
            self.assertEqual(code, 1)
            self.assertIn("ESCALATE", buf.getvalue())
            self.assertEqual(list(dest.glob("po_*.md")), [])

    def test_cli_po_approve_writes_markdown(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.buyer.__main__.OUT", dest):
                code = main(["po", "--spec", "BOX-24", "--approve"])
            self.assertEqual(code, 0)
            self.assertTrue((dest / "po_BOX-24.md").exists())
            self.assertIn("ALLOW", buf.getvalue())

    def test_cli_po_cap_escalates(self) -> None:
        buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            with patch("sys.stdout", buf), patch("domains.buyer.__main__.OUT", dest):
                code = main(["po", "--spec", "BOX-24", "--approve", "--cap-usd", "1"])
            self.assertEqual(code, 1)
            self.assertIn("ESCALATE", buf.getvalue())
            self.assertEqual(list(dest.glob("po_*.md")), [])


if __name__ == "__main__":
    unittest.main()
