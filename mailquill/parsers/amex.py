"""American Express Taiwan monthly statement parser.

The Taiwan PDF uses Chinese ``M月D日`` dates and keeps the TWD amount in the
last column. Some PDFs omit a usable ToUnicode map; extractors then render
``年/月/日`` as stable substitute glyphs. Accept those forms so numeric evidence
remains usable without guessing corrupted merchant text.

Payments are not purchases and are negative in this statement layout, so this
first parser intentionally imports positive card charges only.
"""
from __future__ import annotations

import re

from mailquill.gmail_message import EmailMessage
from mailquill.raw_txn import RawTxn
from mailquill.parsers.base import Parser
from mailquill.parsers._util import md_to_date


_PERIOD_RE = re.compile(
    r"\b(20\d{2})[年ûß](\d{1,2})[月úœ](\d{1,2})[日ùø]"
)
_ACCOUNT_RE = re.compile(r"\b(\d{11,15})\b")
_TXN_RE = re.compile(
    r"^\s*(\d{1,2})[月úœ](\d{1,2})[日ùø]\s+"
    r"(\d{1,2})[月úœ](\d{1,2})[日ùø]\s+"
    r"(.+?)\s+(-?[\d,]+)\s*$"
)


class AmexParser(Parser):
    bank = "Amex"

    def matches(self, msg: EmailMessage) -> bool:
        sender = msg.sender.lower()
        return "americanexpress.com" in sender or "aexp.com" in sender

    def parse(self, msg: EmailMessage, pdf_texts: list[str]) -> list[RawTxn]:
        blocks = [msg.body_text] + list(pdf_texts)
        combined = "\n".join(blocks)
        period = _PERIOD_RE.search(combined)
        account = _ACCOUNT_RE.search(combined)
        if not period or not account:
            return []

        statement_year = int(period.group(1))
        statement_month = int(period.group(2))
        account_last4 = account.group(1)[-4:]
        transactions: list[RawTxn] = []

        for block in blocks:
            for line in block.splitlines():
                match = _TXN_RE.match(line)
                if not match:
                    continue
                transaction_month, transaction_day, post_month, post_day, merchant, amount = (
                    match.groups()
                )
                if amount.startswith("-"):
                    continue
                merchant = " ".join(merchant.split()).strip()
                if not merchant:
                    continue
                transactions.append(
                    RawTxn(
                        bank=self.bank,
                        date=md_to_date(
                            transaction_month.zfill(2),
                            transaction_day.zfill(2),
                            statement_year,
                            statement_month,
                        ),
                        post_date=md_to_date(
                            post_month.zfill(2),
                            post_day.zfill(2),
                            statement_year,
                            statement_month,
                        ),
                        amount=amount,
                        merchant_raw=merchant,
                        account_last4=account_last4,
                        currency="TWD",
                    )
                )
        return transactions
