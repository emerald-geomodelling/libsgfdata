import re
import pkg_resources
import pandas as pd
import numpy as np
import slugify
import codecs
import copy
import dateutil.parser
import datetime
import logging
from pathlib import Path
import sys
import cchardet as chardet
from . import metadata

logger = logging.getLogger(__name__)

def _unconv(b, k, v):
    if k == "DatumTid":
        return v.strftime("%Y%m%d%H%M%S%f")[:-3] # Milliseconds are not supported by strftime, so use %f and remove three decimals
    elif isinstance(v, datetime.date):
        return v.strftime("%Y%m%d")
    elif isinstance(v, datetime.datetime):
        return v.strftime("%Y%m%d%H%M")
    else:
        return str(v)

def _dump_line(block, line):
    return ",".join("%s=%s" % (k,_unconv(block, k, v))
                    for k,v in line.items()
                    if str(v) and (not isinstance(v, float) or not np.isnan(v)))

def _dump_raw(sections, output_filename=None, *arg, **kw):
    if isinstance(output_filename, str):
        with open(output_filename, "wb") as f:
            _dump_raw_to_file(sections, f, *arg, **kw)
    elif output_filename is not None:
        _dump_raw_to_file(sections, output_filename, *arg, **kw)
    else:
        raise NotImplementedError

def _dump_raw_to_file(sections, f, encoding="latin-1"):
    f = codecs.getwriter(encoding)(f, errors='ignore')
    for section in sections:
        for blockname in ("$", "£", "#", "€", "#$"):
            if blockname == "$" or (blockname in section and section[blockname]):
                f.write(blockname + "\n")
                for row in section.get(blockname, []):
                    f.write(_dump_line(metadata.blocknames[blockname], row) + "\n")

def _unrename_blocks(sections):
    for idx in range(len(sections)):
        sections[idx] = {metadata.unblocknames.get(name, name): block
                         for name, block in sections[idx].items()}

def _unmake_dfs(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].to_dict('records')

def _unrename_data_columns(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].rename(columns = metadata.undata.code.to_dict())

def _unrename_main(sections):
    for idx in range(len(sections)):
        sections[idx]["main"] = [
            {metadata.unmain.loc[key, "code"] if key in metadata.unmain.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["main"]]

def _unrename_method(sections):
    for idx in range(len(sections)):
        if "method" not in sections[idx]:
            continue
        sections[idx]["method"] = [
            {metadata.unmethod.loc[key, "code"] if key in metadata.unmethod.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["method"]]
        
def _unrename_values_method_code(sections):
    for section in sections:
        for row in section["main"]:
            if 'method_code' in row:
                code = str(row['method_code'])
                if code in metadata.unmethods.index:
                    row['method_code'] = metadata.unmethods.loc[code, "code"]

def _unrename_values_comments(sections):
    key = "comments"
    for section in sections:
        if key in section["data"].columns:
            codes = section["data"][key]
            missing = list(set(codes.unique()) - set(metadata.uncomments.index))
            labels = pd.concat((metadata.uncomments,
                                pd.DataFrame([{"code": code} for code in missing], index=missing)))
            section["data"][key] = labels.loc[codes, "code"].values

def _unrename_values_data_flags(sections):
    key = "allocated_value_during_performance_of_sounding"
    for section in sections:
        if key in section["data"].columns:
            codes = section["data"][key]
            missing = list(set(codes.unique()) - set(metadata.undata_flags.index))
            labels = pd.concat((metadata.undata_flags,
                                pd.DataFrame([{"code": code} for code in missing], index=missing)))
            section["data"][key] = labels.loc[codes, "code"].values
                    
def dump(sections, *arg, **kw):
    sections = copy.deepcopy(sections)    
    _unrename_values_data_flags(sections)
    _unrename_values_comments(sections)
    _unrename_data_columns(sections)
    _unmake_dfs(sections)
    _unrename_method(sections)
    _unrename_values_method_code(sections)
    _unrename_main(sections)
    _unrename_blocks(sections)
    sections = _dump_raw(sections, *arg, **kw)
    return sections
