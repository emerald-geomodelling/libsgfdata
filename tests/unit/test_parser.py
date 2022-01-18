import pytest

from libsgfdata.parser import _parse_line


class TestParseLine:

    @pytest.mark.parametrize('line, test_case', [
        ('D=10.500,A=7.363,B=1.013,AP=1,R=0,P=0.199,PR=0.269,I=0.747,SP=11.672,J=12.601,', 'WRONG_TYPE'), ])
    def test_parse_line(self, line: str, test_case: str):
        """
        Test special real world data rows encountered in the wild
        """
        parsed_line = _parse_line('data', line)

        if test_case == 'WRONG_TYPE':
            assert type(parsed_line['J']) == float
