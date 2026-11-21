import pyarrow as pa
import pytest

from type_map import arrow_type


def test_integers():
    assert arrow_type("bigint") == pa.int64()
    assert arrow_type("smallint") == pa.int16()


def test_decimal_keeps_precision_and_scale():
    assert arrow_type("decimal", 18, 2) == pa.decimal128(18, 2)


def test_text_types_are_strings():
    for t in ("char", "varchar", "nvarchar"):
        assert arrow_type(t) == pa.string()


def test_date_and_timestamp():
    assert arrow_type("date") == pa.date32()
    assert arrow_type("datetime2", 27, 7) == pa.timestamp("us")


def test_unknown_type_fails_loudly():
    with pytest.raises(ValueError):
        arrow_type("geography")