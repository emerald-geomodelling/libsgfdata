# Changelog

## 0.0.25

### Fixed
- Make coordinate normalization work on pandas 3.x and silence the
  `DataFrameGroupBy.apply operated on the grouping columns` `FutureWarning` on
  pandas 2.2+ (#50). The two `groupby(...).apply(...)` calls in `normalizer.py`
  read the grouping columns (`projection_orig`, `projection`) from inside the
  group frame, which pandas 3.0 excludes by default (raising `AttributeError`)
  and pandas 2.2+ warns about. Replaced them with a version-agnostic
  `_apply_by_group` helper that keeps the grouping columns available and
  preserves original row order, working across pandas 1.x/2.x/3.x without the
  `include_groups` keyword.
- correct numpy spellings for version 2, including `np.NaN`-> `np.nan`

### Changed
- Require `pandas>=2`.

## 0.0.24

### Changed
- Migrate off `pkg_resources` (removed in setuptools 81) to `importlib.resources`
  for loading bundled CSV metadata; removed unused `pkg_resources` imports in
  `parser.py` and `dumper.py`.

### Fixed (since 0.0.23)
- Allow `z_orig` to be not-null even when `z_coordinate` is null; stop assuming
  `id_col == 'investigation_point'`.
- Downgrade missing-`z_orig` `ValueError` to a warning.
- Handle a mix of `z_coordinate`/`z_orig` NaN vs non-NaN values in the normalizer.
