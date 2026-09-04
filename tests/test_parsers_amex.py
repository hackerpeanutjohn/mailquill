"""American Express Taiwan parser tests with synthetic statement text."""
from mailquill.gmail_message import EmailMessage
from mailquill.parsers import get_parser
from mailquill.parsers.amex import AmexParser


# Synthetic fixture: 9999 intentionally exercises account mapping.
_STATEMENT = """\
美國運通卡 月結單
帳單編號 00000009999 結帳日期 2025年2月1日
消費日期 入帳日期 消費明細 外幣金額 新台幣
1月15日 1月15日 您繳納之帳款已收到 -9,999
1月2日 1月3日 某海外服務 SAN FRANCISCO 1,100
1月4日 1月5日 SOME SERVICE NEW YORK 12.34 2,200
1月30日 1月31日 某醫療 台北分店 3,300
"""


def _message(sender="statement@americanexpress.com"):
    return EmailMessage(
        msg_id="m1",
        sender=sender,
        subject="美國運通電子帳單",
        date="",
        body_text="",
        attachments=[],
    )


def test_amex_parser_matches_sender():
    assert isinstance(get_parser(_message()), AmexParser)
    assert AmexParser().matches(_message("statement@aexp.com"))


def test_amex_parses_twd_charge_column_and_skips_payment():
    transactions = AmexParser().parse(_message(), [_STATEMENT])
    assert len(transactions) == 3
    assert sum(int(item.amount.replace(",", "")) for item in transactions) == 6600
    assert all("繳納" not in item.merchant_raw for item in transactions)

    foreign = next(item for item in transactions if item.merchant_raw.startswith("SOME SERVICE"))
    assert foreign.amount == "2,200"
    assert foreign.date == "2025-01-04"
    assert foreign.post_date == "2025-01-05"
    assert foreign.account_last4 == "9999"
    assert foreign.currency == "TWD"


def test_amex_accepts_pdf_font_fallback_date_markers():
    text = "00000009999 2025ß2œ1ø\n1œ30ø 1œ31ø TEST MERCHANT 777\n"
    transactions = AmexParser().parse(_message(), [text])
    assert len(transactions) == 1
    assert transactions[0].date == "2025-01-30"
    assert transactions[0].post_date == "2025-01-31"


def test_amex_requires_statement_date_and_account_number():
    assert AmexParser().parse(_message(), ["8月3日 8月4日 某商店 500"]) == []
