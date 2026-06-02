import warnings

import numpy as np
import pandas as pd
import pytest

from libsgfdata.normalizer import _apply_by_group


class TestApplyByGroup:

    def _frame(self):
        # Two CRS groups plus one row with a NaN grouping key (must be dropped,
        # matching groupby's default dropna=True). Deliberately interleaved so
        # row-order preservation is actually exercised.
        return pd.DataFrame({
            "projection_orig": [3006, 3007, 3006, np.nan, 3007],
            "value": [10, 20, 30, 40, 50],
        })

    def test_preserves_row_order_and_drops_nan_key(self):
        df = self._frame()
        result = _apply_by_group(df, "projection_orig", lambda x, key: x)
        # NaN-key row (index 3) dropped; remaining rows keep their original order.
        assert list(result.index) == [0, 1, 2, 4]
        assert list(result["value"]) == [10, 20, 30, 50]

    def test_grouping_column_present_in_group_frame(self):
        df = self._frame()
        seen_columns = []

        def capture(group_df, key):
            seen_columns.append(list(group_df.columns))
            return group_df

        _apply_by_group(df, "projection_orig", capture)
        # The grouping column must remain available to the callback on every group.
        assert all("projection_orig" in cols for cols in seen_columns)

    def test_key_passed_for_single_and_multi_key(self):
        df = self._frame()

        single_keys = []
        _apply_by_group(df, "projection_orig",
                        lambda x, key: single_keys.append(key) or x)
        assert set(single_keys) == {3006, 3007}

        multi_keys = []
        df2 = df.assign(projection=4326)
        _apply_by_group(df2, ["projection_orig", "projection"],
                        lambda x, key: multi_keys.append(key) or x)
        assert set(multi_keys) == {(3006, 4326), (3007, 4326)}

    def test_no_future_warning(self):
        df = self._frame()
        with warnings.catch_warnings():
            warnings.simplefilter("error", FutureWarning)
            _apply_by_group(df, "projection_orig", lambda x, key: x)

    def test_empty_input_returns_empty_frame(self):
        df = self._frame().iloc[0:0]
        result = _apply_by_group(df, "projection_orig", lambda x, key: x)
        assert len(result) == 0
        assert list(result.columns) == list(df.columns)
