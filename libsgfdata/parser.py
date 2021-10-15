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
from . import normalizer
from . import metadata

logger = logging.getLogger(__name__)


_RE_FLOAT = re.compile(r"^\s*[-+]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][-+]?[0-9]+)?\s*$")
_RE_INT = re.compile(r"^\s*[-+]?[0-9]+\s*$")
# Fields are generally separated by "," and contain a single "="
# separating the key from the value. However, some fields have values
# containing ",", with no quoting. To handle this, we require the key
# to contain only a-z and A-Z. In addition, the Geotech AB extension,
# have date fields (key "%") with no "=" separating the key from the
# value...
_RE_FIELD_SEP = re.compile(r",(?:(?=[a-zA-Z])|(?=%))")

def _conv(b, k, v):
    conv = metadata.block_metadata[b].conv.get(k, np.nan)
    if conv is not np.nan:
        return conv(v)        
    if v and re.match(_RE_INT, v):
        return int(v)
    elif v and re.match(_RE_FLOAT, v):
        return float(v)
    return v

def _parse_line(block, line):
    try:
        if not line.strip():
            return {}
        return {k:_conv(block, k, v)
                for k, v in (i.split("=", 1) if "=" in i else [i[0], i[1:]]
                             for i in re.split(_RE_FIELD_SEP, line))}
    except Exception as e:
        raise Exception("%s: %s" % (e, line))

def _parse_raw(input_filename, *arg, **kw):
    if isinstance(input_filename, str):
        with open(input_filename, "rb") as f:
            return _parse_raw_from_file(f, *arg, **kw)
    else:
        return _parse_raw_from_file(input_filename, *arg, **kw)

    
def _parse_raw_from_file(f, encoding=None):
    if encoding is None:
        sample = f.read(4096)
        detection = chardet.detect(sample)
        if detection["confidence"] < 0.85:
            encoding = 'latin-1'
        else:
            encoding = detection["encoding"]
        f.seek(0)

    f = codecs.getreader(encoding)(f, errors='ignore')
    sections = []
    blocks = None
    block = None
    for row in f:
        row = row.rstrip("\n\r")
        if row == "$":
            blocks = {"£":[], "$":[], "#":[], "€": []}
            sections.append(blocks)
        if row in ("£", "$", "#", "€", "#$"):
            block = row
        elif block in blocks:
            blocks[block].append(_parse_line(metadata.blocknames[block], row))
    return sections

def _rename_blocks(sections):
    for idx in range(len(sections)):
        sections[idx] = {metadata.blocknames.get(name, name): block
                         for name, block in sections[idx].items()}

def _make_dfs(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            if sections[idx]["data"]:
                sections[idx]["data"] = pd.DataFrame(sections[idx]["data"])
            else:
                del sections[idx]["data"]

def _rename_data_columns(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].rename(columns = metadata.data.ident.to_dict())

def _rename_main(sections):
    for idx in range(len(sections)):
        sections[idx]["main"] = [
            {metadata.main.loc[key, "ident"] if key in metadata.main.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["main"]]

def _rename_method(sections):
    for idx in range(len(sections)):
        sections[idx]["method"] = [
            {metadata.method.loc[key, "ident"] if key in metadata.method.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["method"]]
        
def _rename_values_method_code(sections):
    for section in sections:
        for row in section["main"]:
            if 'method_code' in row:
                code = str(row['method_code'])
                if code in metadata.methods.index:
                    row['method_code'] = metadata.methods.loc[code, "ident"]

def _rename_values_comments(sections):
    for section in sections:
        if "data" in section and "comments" in section["data"].columns:
            def convert(x):
                try:
                    return int(x)
                except:
                    return x
            codes = section["data"].comments.fillna(-1).apply(convert)
            missing = list(set(codes.unique()) - set(metadata.comments.index))
            labels = pd.concat((metadata.comments,
                                pd.DataFrame([{"ident": code} for code in missing], index=missing)))
            section["data"]["comments"] = labels.loc[codes, "ident"].values

def _rename_values_data_flags(sections):
    key = "allocated_value_during_performance_of_sounding"
    for section in sections:
        if "data" in section and key in section["data"].columns:
            codes = section["data"][key].fillna(-1).astype(int)
            missing = list(set(codes.unique()) - set(metadata.data_flags.index))
            labels = pd.concat((metadata.data_flags,
                                pd.DataFrame([{"ident": code} for code in missing], index=missing)))
            section["data"][key] = labels.loc[codes, "ident"].values
            
def parse(*arg, **kw):
    normalize = kw.pop("normalize", False)
    sections = _parse_raw(*arg, **kw)
    _rename_blocks(sections)
    _rename_main(sections)
    _rename_values_method_code(sections)
    _rename_method(sections)
    _make_dfs(sections)
    _rename_data_columns(sections)
    _rename_values_comments(sections)
    _rename_values_data_flags(sections)
    if normalize:
        normalizer.normalize(sections)
    return sections
