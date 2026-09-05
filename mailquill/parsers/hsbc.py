"""HSBC Taiwan credit-card statement parser.

Some HSBC Taiwan PDFs omit usable text mappings for Chinese glyphs. Dates and
TWD amounts remain extractable, so transactions can still be reconciled. When
the merchant text is absent, keep an explicit evidence limitation instead of
guessing a merchant.
"""
from __future__ import annotations

import re

from mailquill.gmail_message import EmailMessage
from mailquill.parsers._util import md_to_date
from mailquill.parsers.base import Parser
from mailquill.raw_txn import RawTxn


_CLOSING_RE = re.compile(
    r"^\s*(20\d{2})/(\d{2})/(\d{2})\s+/\s+-[\d,]+\s+[\d,]+\s*$",
    re.MULTILINE,
)
_TXN_RE = re.compile(
    r"^\s*(\d{2})/(\d{2})\s+(\d{2})/(\d{2})"
    r"(?:\s+(.+?))?\s+(-?[\d,]+)\s*$"
)
_MISSING_MERCHANT = "HSBC statement transaction (text unavailable)"


class HsbcParser(Parser):
    bank = "HSBC"

    def matches(self, msg: EmailMessage) -> bool:
        return "hsbc.com.tw" in msg.sender.lower()

    def parse(self, msg: EmailMessage, pdf_texts: list[str]) -> list[RawTxn]:
        blocks = [msg.body_text] + list(pdf_texts)
        closing = _CLOSING_RE.search("\n".join(blocks))
        if not closing:
            return []

        statement_year = int(closing.group(1))
        statement_month = int(closing.group(2))
        transactions: list[RawTxn] = []

        for block in blocks:
            for line in block.splitlines():
                match = _TXN_RE.match(line)
                if not match:
                    continue
                transaction_month, transaction_day, post_month, post_day, merchant, amount = (
                    match.groups()
                )
                # The statement's payment row shares the transaction layout.
                if amount.startswith("-"):
                    continue
                merchant = " ".join((merchant or "").split()).strip()
                transactions.append(
                    RawTxn(
                        bank=self.bank,
                        date=md_to_date(
                            transaction_month,
                            transaction_day,
                            statement_year,
                            statement_month,
                        ),
                        post_date=md_to_date(
                            post_month,
                            post_day,
                            statement_year,
                            statement_month,
                        ),
                        amount=amount,
                        merchant_raw=merchant or _MISSING_MERCHANT,
                        currency="TWD",
                    )
                )
        return transactions
