"""HSBC Taiwan parser tests with synthetic statement text only."""
from mailquill.gmail_message import EmailMessage
from mailquill.parsers import get_parser
from mailquill.parsers.hsbc import HsbcParser


_STATEMENT = """\
HSBC Credit Card Statement
2027/04/25 400,000
2027/04/07 / -400,000 77,777
03/10 03/10 -400,000
03/12 03/13 FIRST SHOP TAIPEI TW 111
03/20 03/21 SECOND SHOP TAIPEI TW 222
04/01 04/02 THIRD SHOP TAIPEI TW 333
04/05 04/06 FOURTH SHOP TAIPEI TW 444
1,110
"""


def _message(sender="statement@notification.hsbc.com.tw"):
    return EmailMessage(
        msg_id="m1",
        sender=sender,
        subject="HSBC credit card statement",
        date="",
        body_text="",
        attachments=[],
    )


def test_hsbc_parser_matches_taiwan_sender():
    assert isinstance(get_parser(_message()), HsbcParser)


def test_hsbc_parses_twd_charges_and_skips_payment():
    transactions = HsbcParser().parse(_message(), [_STATEMENT])
    assert len(transactions) == 4
    assert sum(int(item.amount.replace(",", "")) for item in transactions) == 1110
    assert transactions[0].date == "2027-03-12"
    assert transactions[-1].post_date == "2027-04-06"
    assert all(not item.amount.startswith("-") for item in transactions)
    assert all(item.currency == "TWD" for item in transactions)


def test_hsbc_keeps_explicit_merchant_and_labels_missing_pdf_text():
    text = """\
2028/02/20 9,999
2028/02/06 / -8,888 1,111
01/12 01/13 555
02/03 02/04 TEST SHOP 556
"""
    transactions = HsbcParser().parse(_message(), [text])
    assert transactions[0].merchant_raw == "HSBC statement transaction (text unavailable)"
    assert transactions[1].merchant_raw == "TEST SHOP"


def test_hsbc_requires_closing_date_signature():
    assert HsbcParser().parse(_message(), ["03/04 03/05 TEST SHOP 500"]) == []
