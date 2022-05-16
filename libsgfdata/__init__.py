from .metadata import main, method, data, methods, comments
from .parser import parse
from .dumper import dump
from .normalizer import normalize
import pandas as pd

def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res

def sections_to_geotech_set(sections, merge=False, id_col="investigation_point"):
    unique_ids = set([borehole["main"][0][id_col] for borehole in sections])
    assert len(unique_ids) == len(sections), "%s is not unique for each borehole" % id_col

    if merge:
        main = pd.DataFrame([merge_dicts(*borehole["main"]) for borehole in sections])
    else:
        main = pd.concat([
            pd.DataFrame(borehole["main"]).assign(**{id_col: borehole["main"][0][id_col]})
            for borehole in sections
            if "main" in borehole])
    
    data = pd.concat([
        borehole["data"].assign(investigation_point=borehole["main"][0][id_col])
        for borehole in sections
        if "data" in borehole])
    method = pd.concat([
        pd.DataFrame(borehole["method"]).assign(investigation_point=borehole["main"][0][id_col])
        for borehole in sections
        if "method" in borehole])
    return {"main": main, "data": data, "method": method}

def geotech_set_to_sections(geotech, id_col="investigation_point"):
    return [{"main": [row.to_dict() for idx, row
                      in geotech["main"][geotech["main"][id_col] == section_id].iterrows()],
      "data": geotech["data"][geotech["data"][id_col] == section_id],
      "method": [method_row for method_idx, method_row
                 in geotech["method"][geotech["method"][id_col] == section_id].iterrows()]
     } for section_id in geotech["main"][id_col].unique()]

_dump_function = dump
_normalize_function = normalize

class SGFData(object):
    def __new__(cls, *arg, **kw):
        self = object.__new__(cls)
        if arg or kw:
            self.id_col = kw.pop("id_col", "investigation_point")
            if arg and isinstance(arg[0], dict):
                self.model_dict = arg[0]
            elif arg and isinstance(arg[0], list):
                self.model_dict = sections_to_geotech_set(arg[0], id_col=self.id_col)
            else:
                self.model_dict = sections_to_geotech_set(parse(*arg, **kw), id_col=self.id_col)
        return self

    def dump(self, *arg, **kw):
        _dump_function(self.sections, *arg, **kw)

    def normalize(self):
        sections = self.sections
        for section in sections:
            if "data" in section:
                section["data"] = section["data"].copy()
        _normalize_function(sections)
        return type(self)(sections)
        
    @property
    def sections(self):
        return geotech_set_to_sections(self.model_dict, id_col=self.id_col)
        
    @property
    def main(self):
        return self.model_dict["main"]
    
    @property
    def data(self):
        return self.model_dict["data"]

    @property
    def method(self):
        return self.model_dict["method"]

    def __repr__(self):
        res = [
            "Geotechnical data",
            "===================",
            "Soundings: %s" % (len(self.main),),
            repr(self.main[["x_coordinate", "y_coordinate"]].describe().loc[["min", "max"]])]

        for col in ("depth", "feed_thrust_force"):
            res.append(repr(pd.DataFrame(self.data[col].describe())))

        return "\n".join(res)
