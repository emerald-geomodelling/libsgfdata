import logging
from . import metadata
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def project(innproj, utproj, xinn, yinn):
    import pyproj
    return pyproj.Transformer.from_crs(
        int(innproj), int(utproj), always_xy=True).transform(xinn, yinn)

def normalize_coordinates(sgf, projection=None, **kw):
    if "projection" not in sgf.main.columns:
        return
    
    if projection is None:
        projection = sgf.main.projection.iloc[0]

    if "projection_orig" not in sgf.main.columns:
        sgf.main["projection_orig"] = sgf.main.projection
        sgf.main = sgf.main.rename(columns={
            "x_coordinate":"x_orig",
            "y_coordinate":"y_orig"})

    # FIXME: Don't reproject unnecessarily
        
    def reproject(df):
        src = df.projection_orig.iloc[0]
        df["x_coordinate"], df["y_coordinate"] = project(src, projection, df["x_orig"].values, df["y_orig"].values)
        df["x_web"], df["y_web"] = project(src, 3857, df["x_orig"].values, df["y_orig"].values)
        df["lon"], df["lat"] = project(src, 4326, df["x_orig"].values, df["y_orig"].values)
        return df
        
    sgf.main = sgf.main.groupby("projection_orig", group_keys=False).apply(reproject)
    sgf.main["projection"] = projection

def normalize_stop_code(sgf):
    if sgf.data is None: return
    if "comments" not in sgf.data.columns: return
    if "stop_code" not in sgf.main.columns:
        data.main["stop_code"] = "no_comment"
    last_comment = sgf.main[["investigation_point"]].merge(
        sgf.data.groupby(sgf.id_col).comments.last().rename("last_comment"),
        left_on="investigation_point", right_index=True, how="left")
    sgf.main["stop_code"] = np.where(pd.isnull(sgf.main.stop_code), last_comment.last_comment, sgf.main.stop_code)
    
def normalize_columns(sgf):
    for blockname, block in sgf.model_dict.items():
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

def normalize_depth(sgf):
    if sgf.data is None: return
    if not len(sgf.data): return
    if "depth" not in sgf.data.columns: return
    
    for col in ("depth", "depth_min", "depth_max"):
        if col not in sgf.main.columns:
            sgf.main[col] = np.nan
    
    sgf.data["depth"] = sgf.data.depth.abs()
    
    last_depth = sgf.main[["investigation_point"]].merge(
        sgf.data.groupby(sgf.id_col).depth.max().rename("last_depth"),
        left_on="investigation_point", right_index=True, how="left")
    
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
    
    sgf.main["depth_max_drilled"] = last_depth.last_depth

def normalize_id(sgf):
    sgf.main[sgf.id_col] = sgf.main[sgf.id_col].astype(str)
    if sgf.data is not None: sgf.data[sgf.id_col] = sgf.data[sgf.id_col].astype(str)
    if sgf.method is not None: sgf.method[sgf.id_col] = sgf.method[sgf.id_col].astype(str)
    
def normalize_order(sgf):
    sgf.main.sort_values([sgf.id_col], inplace=True)
    sgf.data.sort_values([sgf.id_col, "depth"], inplace=True)

    sgf.main.reset_index(inplace=True, drop=True)
    if sgf.data is not None: sgf.data.reset_index(inplace=True, drop=True)
    if sgf.method is not None: sgf.method.reset_index(inplace=True, drop=True)
    
def normalize(sgf, sort=False, **kw):
    normalize_columns(sgf)
    normalize_stop_code(sgf)
    normalize_depth(sgf)
    normalize_coordinates(sgf, **kw)
    normalize_id(sgf)
    if sort:
        normalize_order(sgf)
        
