import numpy as np

def validate_depth_min(sgf):
    if "depth_max_drilled" not in sgf.main.columns or 'depth_min' not in sgf.main.columns:
        return np.ones(len(sgf.main), bool)
    return np.isnan(sgf.main["depth_min"]) | np.isnan(sgf.main["depth_max_drilled"]) | (sgf.main["depth_min"] <= sgf.main["depth_max_drilled"])

def validate_depth_depth_min(sgf):
    if "depth_min" not in sgf.main.columns or 'depth' not in sgf.main.columns:
        return np.ones(len(sgf.main), bool)
    return np.isnan(sgf.main["depth"]) | np.isnan(sgf.main["depth_min"]) | (sgf.main["depth"] >= sgf.main["depth_min"])

def validate_depth_depth_max_drilled(sgf):
    if "depth_max_drilled" not in sgf.main.columns or 'depth' not in sgf.main.columns:
        return np.ones(len(sgf.main), bool)
    return np.isnan(sgf.main["depth"]) | np.isnan(sgf.main["depth_max_drilled"]) | (sgf.main["depth"] <= sgf.main["depth_max_drilled"])

def validate(sgf):
    correct = validate_depth_min(sgf)
    correct = correct & validate_depth_depth_min(sgf)
    correct = correct & validate_depth_depth_max_drilled(sgf)
    sgf.main["errors"] = ~correct
