"""台新銀行（Taishin / Richart）信用卡電子帳單 parser。

明細欄序：消費日 入帳起息日 消費明細 新臺幣金額 [外幣折算日 消費地 幣別 外幣金額]
例：  115/05/25 115/05/26 某商店TAIPEI 1,234 TW

特點：
- 日期為完整民國日期（115/05/25），直接轉西元、不需補年份。
- 卡號末四碼在卡別標題行「(卡號末四碼:9999)」。
- 新臺幣金額為描述之後第一個純數字 token（其後可能接消費地/幣別/外幣金額）。
"""
from __future__ import annotations

import re

from mailquill.gmail_message import EmailMessage
from mailquill.raw_txn import RawTxn
from mailquill.parsers.base import Parser
from mailquill.parsers._util import roc_date_to_iso

_TXN = re.compile(r"^(\d{3})/(\d{2})/(\d{2})\s+(\d{3})/(\d{2})/(\d{2})\s+(.+)$")
_CARD = re.compile(r"卡號末四碼[:：]\s*(\d{4})")
_NUM = re.compile(r"-?[\d,]+(?:\.\d+)?")


class TaishinParser(Parser):
    bank = "Taishin"

    def matches(self, msg: EmailMessage) -> bool:
        return "taishinbank.com.tw" in msg.sender or "richart.tw" in msg.sender

    def parse(self, msg: EmailMessage, pdf_texts: list[str]) -> list[RawTxn]:
        blocks = [msg.body_text] + list(pdf_texts)
        txns: list[RawTxn] = []
        last4 = ""
        for block in blocks:
            previous = ""
            for line in block.splitlines():
                s = line.strip()
                m = _TXN.match(s)
                if not m:
                    card = _CARD.search(s)
                    if card:
                        last4 = card.group(1)
                    if s:
                        previous = s
                    continue
                ty, tm, td, py, pm, pd, rest = m.groups()
                tokens = rest.split()
                # 描述之後第一個純數字 token = 新臺幣金額
                idx = next((i for i, t in enumerate(tokens) if _NUM.fullmatch(t)), None)
                if idx is None:
                    continue
                # 新版 PDF 的文字層會把消費明細換到日期列前一行，日期列只剩
                # 日期、金額與幣別。僅在已讀到卡號且前一行不是另一筆日期時採用。
                merchant = " ".join(tokens[:idx]).strip()
                if idx == 0 and last4 and previous and not _TXN.match(previous):
                    merchant = previous
                if not merchant:
                    continue
                txns.append(RawTxn(
                    bank=self.bank,
                    date=roc_date_to_iso(ty, tm, td),        # 消費日
                    post_date=roc_date_to_iso(py, pm, pd),   # 入帳起息日
                    amount=tokens[idx],
                    merchant_raw=merchant,
                    account_last4=last4,
                    currency="TWD",
                ))
                previous = s
        return txns
