import re
import pkg_resources
import pandas as pd
import numpy as np

blocknames = {"£": "method", "$":"main", "#":"data", "€": "method"}

with pkg_resources.resource_stream("libsgfdata", "method.csv") as f:
    method = pd.read_csv(f).set_index("code")
with pkg_resources.resource_stream("libsgfdata", "main.csv") as f:
    main = pd.read_csv(f).set_index("code")
with pkg_resources.resource_stream("libsgfdata", "data.csv") as f:
    data = pd.read_csv(f).set_index("code")

with pkg_resources.resource_stream("libsgfdata", "methods.csv") as f:
    methods = pd.read_csv(f).set_index("code")
with pkg_resources.resource_stream("libsgfdata", "comments.csv") as f:
    comments = pd.read_csv(f).set_index("code")


_RE_FLOAT = re.compile(r"^[-+]?[0-9]*(\.[0-9]*)?(e[-+]?[0-9]+)?$")
_RE_INT = re.compile(r"^[-+]?[0-9]+$")

def _conv(v):
    if v and re.match(_RE_INT, v):
        return int(v)
    elif v and re.match(_RE_FLOAT, v):
        return float(v)
    return v
def _parse_line(line):
    try:
        return {k:_conv(v) for k, v in (i.split("=") for i in re.split(r",(?=[A-Z])", line))}
    except Exception as e:
        raise Exception("%s: %s" % (e, line))

    
def _parse_raw(filename, encoding="latin-1"):
    sections = []
    blocks = None
    block = None
    with open(filename, encoding=encoding) as f:
        for row in f:
            row = row[:-1]
            if row == "$":
                blocks = {"£":[], "$":[], "#":[], "€": []}
                sections.append(blocks)
            if row in ("£", "$", "#", "€", "#$"):
                block = row
            elif block in blocks:
                blocks[block].append(_parse_line(row))

    return sections

def _rename_blocks(sections):
    for idx in range(len(sections)):
        sections[idx] = {blocknames.get(name, name): block
                         for name, block in sections[idx].items()}

def _make_dfs(sections):
    for idx in range(len(sections)):
        if sections[idx]["data"]:
            sections[idx]["data"] = pd.DataFrame(sections[idx]["data"])
        else:
            del sections[idx]["data"]

def _rename_data_columns(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].rename(columns = data.name.to_dict())

def _rename_main(sections):
    for idx in range(len(sections)):
        sections[idx]["main"] = [
            {main.loc[key, "name"] if key in main.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["main"]]

def _rename_method(sections):
    for idx in range(len(sections)):
        sections[idx]["method"] = [
            {method.loc[key, "name"] if key in method.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["method"]]
        
def _rename_values_method_code(sections):
    for section in sections:
        for row in section["main"]:
            if 'Method code' in row:
                code = str(row['Method code'])
                if code in methods.index:
                    row['Method code'] = methods.loc[code, "name"]

def _rename_values_comments(sections):
    for section in sections:
        if "Comments" in section["data"].columns:
            codes = section["data"].Comments.fillna(-1).astype(int)
            missing = list(set(codes.unique()) - set(comments.index))
            labels = pd.concat((comments,
                                pd.DataFrame([{"name": code} for code in missing], index=missing)))
            section["data"]["Comments"] = labels.loc[codes, "name"].values

def parse(*arg, **kw):
    sections = _parse_raw(*arg, **kw)
    _rename_blocks(sections)
    _rename_main(sections)
    _rename_values_method_code(sections)
    _rename_method(sections)
    _make_dfs(sections)
    _rename_data_columns(sections)
    _rename_values_comments(sections)
    return sections

