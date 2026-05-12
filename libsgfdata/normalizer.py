import logging
import warnings

from . import metadata
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _download_transformer_grids(innproj, utproj):
    from pyproj.transformer import TransformerGroup
    tg = TransformerGroup(innproj, utproj)
    n_unavailable = len(tg.unavailable_operations)
    if n_unavailable>0:
        logger.info(f'Downloading {n_unavailable} unavailable transformer grid(s) to improve accuracy...')
        tg.download_grids(verbose=True)

def project(innproj, utproj, xinn, yinn, zinn=None):
    _download_transformer_grids(innproj, utproj)
    import pyproj
    return pyproj.Transformer.from_crs(
        int(innproj), int(utproj), always_xy=True).transform(xinn, yinn, zinn)

def normalize_coordinates(sgf, projection=None, **kw):
    if "projection" not in sgf.main.columns:
        return
    
    if projection is None:
        projection = sgf.main.projection.iloc[0]
        
    if "projection_orig" not in sgf.main.columns:
        sgf.main["projection_orig"] = sgf.main.projection
        sgf.main["x_orig"] = sgf.main.x_coordinate
        sgf.main["y_orig"] = sgf.main.y_coordinate
        if 'z_coordinate' in sgf.main.columns:
            sgf.main["z_orig"] = sgf.main.z_coordinate

    # FIXME: Don't reproject unnecessarily
        
    def reproject_to_all_crs(df, projection):

        src = df.projection_orig.iloc[0]
        outputs_df = reproject_coords_orig_to_new_crs(df, src, projection)
        for col in outputs_df.columns:
            df[col] = outputs_df[col].values


        df["x_web"], df["y_web"] = project(src, 3857, df["x_orig"].values, df["y_orig"].values)
        df["lon"], df["lat"] = project(src, 4326, df["x_orig"].values, df["y_orig"].values)
        return df

    def validate_stored_original_and_new_coordinates_match_within_tolerance(sgf, coordinate_tolerance = 1e-4, **kw):
        coords_new=sgf.main[['x_coordinate','y_coordinate']].copy()
        if 'z_coordinate' in sgf.main.columns:
            coords_new['z_coordinate'] = sgf.main['z_coordinate'].copy()

        coords_reprojected_from_orig = sgf.main.groupby(["projection_orig","projection"], group_keys=False).apply( lambda x: reproject_coords_orig_to_new_crs(x, x.projection_orig.iloc[0], x.projection.iloc[0]))

        if coords_reprojected_from_orig.shape[1]!=coords_new.shape[1]:
            msg = f'one set of stored coordinates is missing a z coordinate, so only x-y coordinates will be verified. ' \
                  f'\noriginal coordinates: {coords_reprojected_from_orig.shape[1]} dimensions\n ' \
                  f'reprojected coordinates: {coords_new.shape[1]}dimensions\n'
            warnings.warn(msg)

        differences = coords_new-coords_reprojected_from_orig
        mask_exceed_tol = np.abs(differences)>coordinate_tolerance
        if np.any(mask_exceed_tol):
            msg = f'The original (x_orig, y_orig, z_orig) and projected (x_coordinate, y_coordinate, z_coordinate) coordinates stored in this dataset differ beyond tolerace of {coordinate_tolerance} when converted to the same CRS. ' \
                  f'Coordinate values were likely changed in one set but not the other. \n '\
                  f'{mask_exceed_tol.value_counts().sort_index()} \nsummary of the differences \n {differences.describe()}\n '
            warnings.warn(msg)

    def reproject_coords_orig_to_new_crs(df, src, projection):
        # Reproject x_orig/y_orig (and z_orig where applicable) to the target CRS.
        # Rows are split into four subsets based on whether z_orig and z_coordinate are NaN,
        # because pyproj's 3D transform poisons x/y outputs with NaN whenever the input z is NaN.
        # Output columns mirror what the caller will overwrite via `df[col] = outputs_df[col].values`,
        # so we include z_coordinate only when it (or z_orig) was in the input — matching the
        # legacy behavior used by validate_stored_original_and_new_coordinates_match_within_tolerance.
        has_z_orig_col = "z_orig" in df.columns
        has_z_coord_col = "z_coordinate" in df.columns

        if not has_z_orig_col and has_z_coord_col:
            warnings.warn(
                f'While attempting to reproject coordinates, the z_coordinate was present but '
                f'z_orig was missing. You might be handling an older dataset. Are you sure that '
                f'the coordinate system stated in sgf.main.projection_orig reflects the vertical '
                f'datum of the z_coordinate values? If so, try copying values from the '
                f'z_coordinate column to a new "z_orig" column.'
            )

        z_orig_isna = df["z_orig"].isna() if has_z_orig_col else pd.Series(True, index=df.index)
        z_coord_isna = df["z_coordinate"].isna() if has_z_coord_col else pd.Series(True, index=df.index)

        out_cols = ["x_coordinate", "y_coordinate"]
        if has_z_coord_col:
            out_cols.append("z_coordinate")
        out = pd.DataFrame(np.nan, index=df.index, columns=out_cols, dtype=float)

        def _reproject_2d(mask):
            if not mask.any():
                return
            xs, ys = project(src, projection,
                             df.loc[mask, "x_orig"].values,
                             df.loc[mask, "y_orig"].values)
            out.loc[mask, "x_coordinate"] = xs
            out.loc[mask, "y_coordinate"] = ys

        def _reproject_3d(mask):
            xs, ys, zs = project(src, projection,
                                 df.loc[mask, "x_orig"].values,
                                 df.loc[mask, "y_orig"].values,
                                 df.loc[mask, "z_orig"].values)
            return xs, ys, zs

        # Case A: z_orig NaN AND z_coordinate NaN (or columns missing).
        # 2D reproject for x/y; z_coordinate stays NaN.
        mask_a = z_orig_isna & z_coord_isna
        _reproject_2d(mask_a)

        # Case B: z_orig present, z_coordinate NaN.
        # 3D reproject and write the converted z. If conversion produces non-finite z
        # (e.g. missing vertical grid), redo x/y in 2D, copy z_orig as z_coordinate, and warn.
        mask_b = (~z_orig_isna) & z_coord_isna
        if mask_b.any():
            xs, ys, zs = _reproject_3d(mask_b)
            ok = np.isfinite(zs)
            b_idx = df.index[mask_b]
            if ok.any():
                ok_idx = b_idx[ok]
                out.loc[ok_idx, "x_coordinate"] = xs[ok]
                out.loc[ok_idx, "y_coordinate"] = ys[ok]
                if has_z_coord_col:
                    out.loc[ok_idx, "z_coordinate"] = zs[ok]
            if (~ok).any():
                fail_idx = b_idx[~ok]
                warnings.warn(
                    f'{(~ok).sum()} rows: z conversion from z_orig produced non-finite '
                    f'values (likely missing vertical-datum grid); copying z_orig to '
                    f'z_coordinate verbatim and reprojecting x/y in 2D.'
                )
                xs2, ys2 = project(src, projection,
                                   df.loc[fail_idx, "x_orig"].values,
                                   df.loc[fail_idx, "y_orig"].values)
                out.loc[fail_idx, "x_coordinate"] = xs2
                out.loc[fail_idx, "y_coordinate"] = ys2
                if has_z_coord_col:
                    out.loc[fail_idx, "z_coordinate"] = df.loc[fail_idx, "z_orig"].values

        # Case C: z_orig NaN, z_coordinate present.
        # Retain existing z_coordinate as-is; reproject x/y in 2D; warn (we have no source
        # of truth for the vertical reprojection).
        mask_c = z_orig_isna & (~z_coord_isna)
        if mask_c.any():
            warnings.warn(
                f'{mask_c.sum()} rows: z_coordinate is defined but z_orig is null; '
                f'retaining stored z_coordinate without vertical reprojection.'
            )
            _reproject_2d(mask_c)
            if has_z_coord_col:
                out.loc[mask_c, "z_coordinate"] = df.loc[mask_c, "z_coordinate"].values

        # Case D: both z_orig and z_coordinate present.
        # 3D reproject, write the converted value, and warn if it differs from the stored
        # z_coordinate by more than 1e-3 units (likely indicates one of the two columns
        # was edited without updating the other).
        mask_d = (~z_orig_isna) & (~z_coord_isna)
        if mask_d.any():
            xs, ys, zs = _reproject_3d(mask_d)
            existing = df.loc[mask_d, "z_coordinate"].values.astype(float)
            with np.errstate(invalid="ignore"):
                diff = np.abs(zs - existing)
                bad = diff > 1e-3
            if np.any(bad):
                warnings.warn(
                    f'{int(bad.sum())} rows: reprojected z (from z_orig) differs from '
                    f'stored z_coordinate by more than 1e-3 (max diff='
                    f'{float(np.nanmax(diff)):.6g}). z_coordinate may have been edited '
                    f'independently of z_orig.'
                )
            out.loc[mask_d, "x_coordinate"] = xs
            out.loc[mask_d, "y_coordinate"] = ys
            if has_z_coord_col:
                out.loc[mask_d, "z_coordinate"] = zs

        return out

    validate_stored_original_and_new_coordinates_match_within_tolerance(sgf, **kw)
    sgf.main = sgf.main.groupby("projection_orig", group_keys=False).apply(lambda x: reproject_to_all_crs(x, projection))
    sgf.main["projection"] = projection

def normalize_stop_code(sgf):
    if sgf.data is None: return
    if "comments" not in sgf.data.columns: return
    if "stop_code" not in sgf.main.columns:
        sgf.main["stop_code"] = "no_comment"
    if ("title" in sgf.data.columns) & (sgf.id_col not in sgf.data.columns):
        sgf.id_col = "title"
        print("investigation_point not in sgf.data.columns, setting sgf.id_col as 'title'")

    last_comment = sgf.main[[sgf.id_col]].merge(
        sgf.data.groupby(sgf.id_col).comments.last().rename("last_comment"),
        left_on=sgf.id_col, right_index=True, how="left")
    sgf.main["stop_code"] = np.where(pd.isnull(sgf.main.stop_code), last_comment.last_comment, sgf.main.stop_code)
    
def normalize_columns(sgf):
    for blockname, block in sgf._model_dict.items():
        if blockname not in metadata.block_metadata:
            continue
        normalization = metadata.block_metadata[blockname].loc[
            ~metadata.block_metadata[blockname].normalization.isna()
        ].set_index("ident").normalization
        normalization = metadata.block_metadata[blockname].loc[normalization].set_index(normalization.index).ident

        for src, dst in normalization.to_dict().items():
            if src in block.columns:
                filt = ~pd.isnull(block[src]) 
                block.loc[filt, dst] = block.loc[filt, src]
                block.drop(columns=[src], inplace=True)
        
        #block.rename(columns=normalization.to_dict(), inplace=True)

def compute_maximum_depth(sgf, data_cols = ("depth", "start_depth", "end_depth")):
    depth_cols = []
    for col in data_cols:
        if col in sgf.data.columns:
            sgf.data[col] = sgf.data[col].abs()
            depth_cols.append(col)
    agg_max = sgf.data.loc[:,[sgf.id_col]+depth_cols].groupby(sgf.id_col).agg('max')
    last_depth = agg_max.max(1).rename('last_depth')
    last_depth = sgf.main[["investigation_point"]].merge(
        last_depth,
        left_on="investigation_point", right_index=True, how="left")

    return last_depth

def normalize_depth(sgf, summarize_depth=True,
                    main_cols = ('depth','depth_min','depth_max'),
                    data_cols = ("depth", "start_depth", "end_depth")):
    for col in main_cols:
        if col not in sgf.main.columns:
            sgf.main[col] = np.nan

    if sgf.data is None: return
    if not len(sgf.data): return
    if not np.any([c in sgf.data.columns for c in data_cols]): return

    if summarize_depth:
        last_depth = compute_maximum_depth(sgf, data_cols=data_cols)

        sgf.main["depth_min"] = np.where(pd.isnull(sgf.main.depth_min),
                                         last_depth.last_depth,
                                         sgf.main.depth_min)
        sgf.main["depth_max"] = np.where(pd.isnull(sgf.main.depth_max),
                                         np.where(sgf.main.stop_code == "stop_against_presumed_rock",
                                                  last_depth.last_depth,
                                                  np.nan),
                                         sgf.main.depth_max)
        sgf.main["depth"] = np.where(pd.isnull(sgf.main.depth) & (sgf.main.depth_min == sgf.main.depth_max),
                                     sgf.main.depth_max,
                                     sgf.main.depth)
    
        sgf.main.loc[last_depth.index, "depth_max_drilled"] = last_depth.last_depth

def normalize_id(sgf):
    sgf.main[sgf.id_col] = sgf.main[sgf.id_col].astype(str)
    if sgf.data is not None: sgf.data[sgf.id_col] = sgf.data[sgf.id_col].astype(str)
    if sgf.method is not None: sgf.method[sgf.id_col] = sgf.method[sgf.id_col].astype(str)
    
def normalize_order(sgf):
    sgf.main.sort_values([sgf.id_col], inplace=True)
    sort_cols = [sgf.id_col]

    if "start_depth" in sgf.data.columns:
        sort_cols.append("start_depth")
    if "depth" in sgf.data.columns:
        sort_cols.append("depth")
    sgf.data.sort_values(sort_cols, inplace=True)

    sgf.main.reset_index(inplace=True, drop=True)
    if sgf.data is not None: sgf.data.reset_index(inplace=True, drop=True)
    if sgf.method is not None: sgf.method.reset_index(inplace=True, drop=True)
    
def normalize(sgf, sort=False, summarize_depth=True, **kw):    
    if "investigation_point" not in sgf.main.columns:
        sgf.main["investigation_point"] = sgf.main.title.copy()
    if "investigation_point" not in sgf.data.columns:
        sgf.data["investigation_point"] = sgf.data.title.copy()

    normalize_columns(sgf)
    normalize_stop_code(sgf)
    normalize_depth(sgf, summarize_depth=summarize_depth)
    normalize_coordinates(sgf, **kw)
    normalize_id(sgf)
    if sort:
        normalize_order(sgf)
        
