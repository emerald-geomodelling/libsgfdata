# Changelog

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
