from .metadata import main, method, data, methods, comments
from .parser import parse
from .dumper import dump
from .normalizer import normalize
import pandas as pd

def sections_to_geotech_set(sections):
    unique_ids = len(set([borehole["main"][0]["investigation_point"] for borehole in sections]))
    assert unique_ids == len(sections), "investigation_point is not unique for each borehole"
    
    main = pd.DataFrame([merge_dicts(*borehole["main"]) for borehole in sections])
    data = pd.concat([
        borehole["data"].assign(investigation_point=borehole["main"][0]["investigation_point"])
        for borehole in sections
        if "data" in borehole])
    method = pd.concat([
        pd.DataFrame(borehole["method"]).assign(investigation_point=borehole["main"][0]["investigation_point"])
        for borehole in sections
        if "method" in borehole])
    return {"main": main, "data": data, "method": method}


def merge_dicts(*dicts):
    res = {}
    for d in dicts:
        res.update(d)
    return res

def geotech_set_to_sections(geotech):
    return [{"main": [row.to_dict()],
      "data": geotech["data"][geotech["data"].investigation_point == row.investigation_point],
      "method": [method_row for method_idx, method_row
                 in geotech["method"][geotech["method"].investigation_point == row.investigation_point].iterrows()]
     } for idx, row in geotech["main"].iterrows()]

_dump_function = dump

class SGFData(object):
    def __new__(cls, *arg, **kw):
        self = object.__new__(cls)
        if arg or kw:
            if arg and isinstance(arg[0], dict):
                self.model_dict = arg[0]
            elif arg and isinstance(arg[0], list):
                self.model_dict = sections_to_geotech_set(arg[0])
            else:
                self.model_dict = sections_to_geotech_set(parse(*arg, **kw))
        return self

    def dump(self, *arg, **kw):
        _dump_function(geotech_set_to_sections(self.model_dict), *arg, **kw)

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
