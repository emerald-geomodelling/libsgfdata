import logging
from . import metadata

logger = logging.getLogger(__name__)

def project(innproj, utproj, xinn, yinn):
    import pyproj
    return pyproj.Transformer.from_crs(
        int(innproj), int(utproj), always_xy=True).transform(xinn, yinn)

def normalize_coordinates(sgf, project_crs=None, **kw):
    if "projection" not in sgf.main.columns:
        return
    
    if project_crs is None:
        project_crs = sgf.main.projection.iloc[0]
    
    sgf.main = sgf.main.rename(columns={
        "x_coordinate":"x_orig",
        "y_coordinate":"y_orig"})

    def reproject(df):
        src = df.projection.iloc[0]
        df["x_coordinate"], df["y_coordinate"] = project(src, project_crs, df["x_orig"].values, df["y_orig"].values)
        df["x_web"], df["y_web"] = project(src, 3857, df["x_orig"].values, df["y_orig"].values)
        df["lon"], df["lat"] = project(src, 4326, df["x_orig"].values, df["y_orig"].values)
        return df
        
    sgf.main = sgf.main.groupby("projection", group_keys=False).apply(reproject)

def normalize_columns(sgf):
    for blockname, block in sgf.model_dict.items():
        normalization = metadata.block_metadata[blockname].loc[
            ~metadata.block_metadata[blockname].normalization.isna()
        ].set_index("ident").normalization
        normalization = metadata.block_metadata[blockname].loc[normalization].set_index(normalization.index).ident
        
        block.rename(columns=normalization.to_dict(), inplace=True)
    
def normalize(sgf, **kw):
    normalize_columns(sgf)
    normalize_coordinates(sgf, **kw)
