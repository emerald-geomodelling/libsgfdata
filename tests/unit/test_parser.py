from datetime import time

import pytest

from libsgfdata.parser import _parse_line


class TestParseLine:

    @pytest.mark.parametrize('block, line, test_case', [
        ('data', 'D=10.500,J=12.601,', 'WRONG_TYPE'),
        ('main', 'HD=20210324,HI=004940,HM=24', 'DATE_FIELD'),
        ('main', 'HD=20210324,HI=2340,HM=24', 'DATE_FIELD'),
        ('main', 'HD=20210324,HI=,HM=24', 'DATE_FIELD'),
    ])
    def test_parse_line(self, block: str, line: str, test_case: str):
        """
        Test special real world data rows encountered in the wild
        """
        parsed_line = _parse_line(block, line)

        if test_case == 'WRONG_TYPE':
            assert type(parsed_line['J']) == float
        elif test_case == 'DATE_FIELD':
            assert type(parsed_line['HI']) == time
