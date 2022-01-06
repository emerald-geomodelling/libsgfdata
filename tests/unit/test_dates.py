import datetime

import pytest

from libsgfdata.parser import _conv

class TestDates:

    @pytest.mark.parametrize("block, key, date_string, expected_result", [
        ("data", "AK", "200208221132", datetime.datetime(2002, 8, 22, 11, 32)),
        ("main", "HD", "20120105", datetime.date(2012, 1, 5)),
        ("main", "HD", "09/04/99", datetime.date(1999, 4, 9)),
        ("main", "HD", "27.06.2014", datetime.date(2014, 6, 27)),
        ("main", "KD", "27.06.2014", datetime.date(2014, 6, 27)),
    ])
    def test_dates(self, block, key, date_string, expected_result):
        assert expected_result == _conv(block, key, date_string)
