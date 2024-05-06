from .metadata import main, method, data, methods, comments
from .parser import parse
from .dumper import dump
from .normalizer import normalize
from .validate import validate
import pandas as pd
import numpy as np
import logging
import copy
import uuid

logger = logging.getLogger(__name__)

def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res

def sections_to_geotech_set(sections, merge=False, id_col="investigation_point"):
    mains = []
    datas = []
    methods = []
    for borehole in sections:
        for key in ['main','data','method']:
            if key not in borehole:
                borehole[key]=[]
        
        if not len(borehole["main"]): borehole["main"].append({})
        if id_col in borehole["main"][0]:
            investigation_point = borehole["main"][0][id_col]
            print("Parsing: ", investigation_point)
        else:
            investigation_point = str(uuid.uuid4())
    
        if merge:
            main = pd.DataFrame([merge_dicts(*borehole["main"])])
        else:
            main = pd.DataFrame(borehole["main"])

        mains.append(main.assign(**{id_col: investigation_point}))
        datas.append(pd.DataFrame(borehole["data"]).assign(**{id_col: investigation_point}))
        methods.append(pd.DataFrame(borehole["method"]).assign(**{id_col: investigation_point}))

    mains = pd.concat(mains, ignore_index=True)
    datas = pd.concat(datas, ignore_index=True)
    methods = pd.concat(methods, ignore_index=True)
    
    unique_ids = set(mains[id_col])
    assert len(unique_ids) == len(sections), "%s is not unique for each borehole" % id_col
        
    return {"main": mains, "data": datas, "method": methods}

def _infer_projection_from_dataframe(dictionary, column='projection'):
    if 'main' not in dictionary:
        return None
    if "projection" not in dictionary['main'].columns:
        return None
    projections = dictionary['main'][column].unique()
    if len(projections) != 1:
        return None
    return int(projections[0])

def geotech_set_to_sections(geotech, id_col="investigation_point"):
    return [{"main": [row.to_dict() for idx, row
                      in geotech["main"][geotech["main"][id_col] == section_id].iterrows()]
                     if "main" in geotech else [],
             "data": geotech["data"][geotech["data"][id_col] == section_id]
                     if "data" in geotech else pd.DataFrame(),
             "method": [method_row for method_idx, method_row
                        in geotech["method"][geotech["method"][id_col] == section_id].iterrows()]
                     if "method" in geotech else pd.DataFrame()
            } for section_id in geotech["main"][id_col].unique()]

_dump_function = dump
_normalize_function = normalize
_validate_function = validate

class SGFData(object):
    def __new__(cls, *arg, **kw):
        normalize = kw.pop("normalize", False)
        encoding = kw.pop("encoding", None)
        validate = kw.pop("validate", False)
        self = object.__new__(cls)
        self._model_dict = {}
        self.id_col = "investigation_point"
        if arg or kw:
            self.id_col = kw.pop("id_col", "investigation_point")
            if arg and isinstance(arg[0], dict):
                self._model_dict = arg[0]
            elif arg and isinstance(arg[0], list):
                self._model_dict = sections_to_geotech_set(arg[0], id_col=self.id_col)
            elif arg and isinstance(arg[0], SGFData):
                for block in ("main", "data", "method"):
                    blockdata = [
                        argi._model_dict[block]
                        for argi in arg
                        if block in argi._model_dict]
                    if blockdata:
                        self._model_dict[block] = pd.concat(blockdata).reset_index(drop=True)
            else:
                self._model_dict = sections_to_geotech_set(parse(*arg, encoding=encoding), id_col=self.id_col)
        if normalize:
            self = self.normalize(**kw)
        if validate:
            self.validate(**kw)
        return self

    def dump(self, *arg, **kw):
        _dump_function(self.sections, *arg, **kw)

    def normalize(self, **kw):
        """Normalizes column names, column dtypes, stop code names,
        depth columns and coordinates.


        Column names:
        Normalized according to the "normalization" column of the
        libsgfdata.metadata.block_metadata[blockname] for each block
        (main, data, method).


        Stop codes:
        main.stop_code is set to the last data.comments


        Depth columns:
        All depths are positive, and deeper positions have higher values.

        main.depth_min contains the minimum (shallowest) depth of a
                       bedrock surface if present and known.

        main.depth_max contains the maximum (deepest) depth of a
                       bedrock surface if present and known.

        main.depth     contains the depth of a bedrock surface if present
                       and known. depth overrides depth_min and depth_max.

        If summarize_depth is True (the default), depth_min, depth_max
        and depth are calculated from data.depth/data.end_depth if not
        already set to a non NaN value.

        main.depth_max_drilled contains the deepest position acquired.


        Coordinates: 
        Normalized to a supplied "projection" epsg code. Old
        coordinates are stored in "x_orig","y_orig", old projection in
        "projection_orig". In addition, coordinates are reprojected to
        WGS84 in "lat","lon", and to spherical mercator in
        "x_web","y_web".

        """
        res = copy.deepcopy(self)
        _normalize_function(res, **kw)
        return res

    def validate(self, **kw):
        _validate_function(self)

    @property
    def model_dict(self):
        return self._model_dict

    @property
    def sections(self):
        return geotech_set_to_sections(self.model_dict, id_col=self.id_col)
    
    @sections.setter
    def sections(self, sections):
        self._model_dict = sections_to_geotech_set(sections, id_col=self.id_col)
            
    @property
    def main(self):
        return self.model_dict.get("main", None)

    @main.setter
    def main(self, a):
        self.model_dict["main"] = a
    
    @property
    def data(self):
        return self.model_dict.get("data", None)

    @data.setter
    def data(self, a):
        self.model_dict["data"] = a

    @property
    def method(self):
        return self.model_dict.get("method", None)

    @method.setter
    def method(self, a):
        self.model_dict["method"] = a
        
    def __repr__(self):
        res = [
            "Geotechnical data",
            "===================",
            "Soundings: %s" % (len(self.main) if self.main is not None else 0,),
            "Depths: %s" % (len(self.data) if self.data is not None else 0,),
            "===================",
            repr(self.main[["x_coordinate", "y_coordinate"]].describe().loc[["min", "max"]],) if self.main is not None else ""]

        if self.data is not None:
            for col in ("depth", "feed_thrust_force"):
                if col in self.data.columns:
                    res.append(repr(pd.DataFrame(self.data[col].describe())))

        return "\n".join(res)

    def sample_dtm(self, raster, overwrite=True):
        from . import dtm
        self.sections = dtm.sample_z_coordinate_from_dtm(self.sections, self.projection, raster=raster, overwrite=overwrite)

    def sample_terrainy_dtm(self, raster_name, overwrite=True):
        import terrainy
        import geopandas as gpd

        assert self.main

        conn = terrainy.connect(raster_name)

        # Buffer 1m, or we can get problems with boreholes right at the tile boundary...
        tiles = gpd.GeoDataFrame(
            geometry=[polygon for x_idx, y_idx, polygon in conn.get_tile_bounds(self.area.buffer(1), 1)],
            crs=conn.get_crs())

        positions = self.positions.to_crs(tiles.crs)
        positions["tile"] = -1
        for idx, tile in enumerate(tiles.geometry):
            positions.loc[positions.within(tile), "tile"] = idx

        tile_idxs = positions.tile.unique()
        for idx, tile_idx in enumerate(tile_idxs):
            logger.info("Working on tile %s of %s" % (idx, len(tile_idxs)))
            filt = positions.tile == tile_idx
            xy = np.column_stack((positions.geometry.x, positions.geometry.y))
            with conn.open_tile(tiles.loc[tile_idx].geometry.bounds, 1) as dataset:
                positions.loc[filt, "topo"] = [v[0] for v in dataset.sample(xy[filt,:])]
                
        self.main["z_coordinate"] = positions.topo
        
    @property
    def projection(self):
        return _infer_projection_from_dataframe(self._model_dict)
    
    @property
    def positions(self):
        import geopandas as gpd

        assert self.main is not None, 'self.main DataFrame is None, so cannot access geographic attributes like positions, area, or bounds'
        assert len(self.main)>0,'self.main DataFrame is either missing or is empty'
        
        projection = self.projection
        if projection is None: raise ValueError("SGF file has boreholes in multiple projections, or projection not specified.")
        
        positions = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(self.main.x_coordinate, self.main.y_coordinate),
            index=self.main.index)
        return positions.set_crs(projection)

    @property
    def area(self):
        """Returns the convex hull of all borehole positions"""
        import geopandas as gpd

        positions = self.positions
        return gpd.GeoDataFrame(geometry=[positions.unary_union.convex_hull]).set_crs(self.positions.crs)
    
    @property
    def bounds(self):
        return self.area.bounds
