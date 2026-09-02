"""統一交易 schema 與 ID 雜湊。"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, fields

FIELDS = [
    "txn_id", "date", "post_date", "amount", "currency",
    "merchant_raw", "merchant_norm", "category_l1", "category_l2",
    "bank", "account_last4", "source_type", "source_msg_id",
    "raw_ref", "imported_at", "seq",
]


def make_txn_id(bank: str, account_last4: str, date: str,
                amount: str, merchant_raw: str, seq: int = 0) -> str:
    """以 source_account+date+amount+merchant+seq 計算去重雜湊。

    seq 是該筆在來源帳單中的出現序號：同一張帳單裡兩筆「同日、同店、同額」
    的真實交易會因 seq 不同而保留兩筆；而同一份帳單不論由 run(Gmail) 或
    ingest(本地檔) 解析，順序一致 → seq 一致 → txn_id 一致 → 自動去重。
    """
    source_account = f"{bank}:{account_last4}"
    key = "|".join([source_account, date, amount, merchant_raw, str(seq)])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


@dataclass
class Transaction:
    txn_id: str
    date: str
    post_date: str
    amount: str
    currency: str
    merchant_raw: str
    merchant_norm: str
    category_l1: str
    category_l2: str
    bank: str
    account_last4: str
    source_type: str
    source_msg_id: str
    raw_ref: str
    imported_at: str
    seq: str = ""
    """該筆在來源帳單中的出現序號（字串）。txn_id 的一部分，必須持久化：

    沒存下來的話，日後只要 make_txn_id 公式改動，就無法從 CSV 重算 id，
    同一筆交易會拿到兩種 id 而重複入帳。空字串代表遷移前的舊資料。
    """

    def to_row(self) -> dict[str, str]:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Transaction":
        # seq 是後加欄位，讀得進遷移前沒有這欄的舊 CSV
        return cls(**{name: row.get(name, "") for name in FIELDS})
