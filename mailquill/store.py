"""CSV 真實來源讀寫（含去重）。SQLite 重建在 Task 3 追加。"""
from __future__ import annotations

import csv
import os
import sqlite3
from dataclasses import dataclass

from mailquill.schema import FIELDS, Transaction


@dataclass
class AppendResult:
    added: int
    skipped: int


def read_transactions(csv_path: str) -> list[Transaction]:
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [Transaction.from_row(row) for row in reader]


def count_legacy_id_rows(csv_path: str) -> int:
    """回傳 seq 為空的列數，也就是 txn_id 還是舊公式（無 seq）算出來的列。

    這些列的 id 無法對上現行公式，同一封信一被重抓就會多長一列，
    所以在抓信前要先提醒跑 migrate-ids。
    """
    return sum(1 for t in read_transactions(csv_path) if t.seq == "")


def append_transactions(csv_path: str, txns: list[Transaction]) -> AppendResult:
    existing_ids = {t.txn_id for t in read_transactions(csv_path)}
    file_exists = os.path.exists(csv_path)
    added = skipped = 0
    batch_ids: set[str] = set()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        for txn in txns:
            if txn.txn_id in existing_ids or txn.txn_id in batch_ids:
                skipped += 1
                continue
            writer.writerow(txn.to_row())
            batch_ids.add(txn.txn_id)
            added += 1
    return AppendResult(added=added, skipped=skipped)


def rebuild_sqlite(csv_path: str, db_path: str) -> int:
    txns = read_transactions(csv_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DROP TABLE IF EXISTS transactions")
        col_defs = ", ".join(
            f"{name} REAL" if name == "amount" else f"{name} TEXT"
            for name in FIELDS
        )
        conn.execute(f"CREATE TABLE transactions ({col_defs})")
        placeholders = ", ".join("?" for _ in FIELDS)
        rows = []
        for t in txns:
            row = t.to_row()
            values = [
                float(row[name]) if name == "amount" and row[name] != "" else row[name]
                for name in FIELDS
            ]
            rows.append(values)
        conn.executemany(
            f"INSERT INTO transactions ({', '.join(FIELDS)}) VALUES ({placeholders})",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    return len(txns)
