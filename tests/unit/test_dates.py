import datetime

import pytest

import libsgfdata as sgf

class TestDates:

    @pytest.mark.parametrize("key, date_string, expected_result", [
        ("AK", "200208221132", datetime.datetime(2002, 8, 22, 11, 32)),
        ("HD", "20120105", datetime.date(2012, 1, 5)),
        ("HD", "09/04/99", datetime.date(1999, 4, 9)),
        ("HD", "27.06.2014", datetime.date(2014, 6, 27)),
    ])
    def test_dates(self, key, date_string, expected_result):
        assert expected_result == sgf._conv(key, date_string)
