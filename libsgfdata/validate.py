def validate_depth_min(sgf):
    return np.isnan(sgf.main["depth_min"]) | np.isnan(sgf.main["depth_max_drilled"]) | (sgf.main["depth_min"] <= sgf.main["depth_max_drilled"])

def validate_depth(sgf):
    return ((np.isnan(sgf.main["depth"]) | np.isnan(sgf.main["depth_min"]) | (sgf.main["depth"] >= sgf.main["depth_min"]))
            &
            (np.isnan(sgf.main["depth"]) | np.isnan(sgf.main["depth_max_drilled"]) | (sgf.main["depth"] <= sgf.main["depth_max_drilled"])))

def validate(sgf):
    correct = validate_depth_min(sgf)
    correct = correct & validate_depth(sgf)
    sgf.main["errors"] = ~correct
