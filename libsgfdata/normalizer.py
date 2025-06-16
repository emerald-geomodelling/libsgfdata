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
            raise ValueError(msg)

    def reproject_coords_orig_to_new_crs(df, src, projection):

        zz = None
        if "z_orig" in df.columns:
            if np.sum(df["z_orig"].isna()) == 0:
                zz = df["z_orig"].values
            elif np.sum(df["z_orig"].isna()) == len(df):
                zz = None
            else:
                msg = f'Found a mix of NaN and non-NaN values in "z_orig" column. The function normalize_coordinates is ' \
                      f'not currently configured to handle a mix of values. "z_orig" must be all NaN or all not NaN.'
                raise ValueError(msg)
        if ('z_coordinate' in df.columns) and ('z_orig' not in df.columns):
            msg = f'While attempting to reproject coordinates, the z_coordinate was present but z_orig was missing. You ' \
                  f'might be handling an older dataset. Are you sure that the coordinate system stated in ' \
                  f'sgf.main.projection_orig reflects the vertical datum of the z_coordinate values? If so, try copying ' \
                  f'values from the z_coordinate column to a new "z_orig" column.'
            warnings.warn(msg)
        outputs_dict = {}
        outputs_tuple = project(src, projection, df["x_orig"].values, df["y_orig"].values, zz)
        outputs_dict["x_coordinate"], outputs_dict["y_coordinate"] = (outputs_tuple[0], outputs_tuple[1])
        if len(outputs_tuple) > 2:
            z_new = outputs_tuple[2]
            outputs_dict["z_coordinate"] = z_new
        return pd.DataFrame(outputs_dict, index=df.index)

    validate_stored_original_and_new_coordinates_match_within_tolerance(sgf, **kw)
    sgf.main = sgf.main.groupby("projection_orig", group_keys=False).apply(lambda x: reproject_to_all_crs(x, projection))
    sgf.main["projection"] = projection

def normalize_stop_code(sgf):
    if sgf.data is None: return
    if "comments" not in sgf.data.columns: return
    if "stop_code" not in sgf.main.columns:
        sgf.main["stop_code"] = "no_comment"
    if ("title" in sgf.data.columns) & ("investigation_point" not in sgf.data.columns):
        sgf.id_col = "title"
        print("investigation_point not in sgf.data.columns, setting sgf.id_col as 'title'")

    last_comment = sgf.main[["investigation_point"]].merge(
        sgf.data.groupby(sgf.id_col).comments.last().rename("last_comment"),
        left_on="investigation_point", right_index=True, how="left")
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
        
