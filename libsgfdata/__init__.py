import re
import pkg_resources
import pandas as pd
import numpy as np
import slugify
import codecs
import copy

blocknames = {"£": "method", "$":"main", "#":"data", "€": "method"}
unblocknames = {v:k for k, v in blocknames.items()}

def _read_csv(f):
    return pd.read_csv(f, na_values=['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
                                     '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NULL', 'NaN', 'n/a', 'nan', 'null'],
                       keep_default_na=False).set_index("code")

with pkg_resources.resource_stream("libsgfdata", "method.csv") as f:
    method = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "main.csv") as f:
    main = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "data.csv") as f:
    data = _read_csv(f)
    
with pkg_resources.resource_stream("libsgfdata", "methods.csv") as f:
    methods = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "comments.csv") as f:
    comments = _read_csv(f)


method["ident"] = method.name.astype(str).apply(lambda x: slugify.slugify(x, separator="_"))
main["ident"] = main.name.astype(str).apply(lambda x: slugify.slugify(x, separator="_"))
data["ident"] = data.name.astype(str).apply(lambda x: slugify.slugify(x, separator="_"))
methods["ident"] = methods.name.astype(str).apply(lambda x: slugify.slugify(x, separator="_"))
comments["ident"] = comments.name.astype(str).apply(lambda x: slugify.slugify(x, separator="_"))

unmethod = method.reset_index().set_index("ident")
unmain = main.reset_index().set_index("ident")
undata = data.reset_index().set_index("ident")
unmethods = methods.reset_index().set_index("ident")
uncomments = comments.reset_index().set_index("ident")

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

def _parse_raw(input_filename, *arg, **kw):
    if isinstance(input_filename, str):
        with open(input_filename, "rb") as f:
            return _parse_raw_from_file(f, *arg, **kw)
    else:
        return _parse_raw_from_file(input_filename, *arg, **kw)

    
def _parse_raw_from_file(f, encoding="latin-1"):
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
            sections[idx]["data"] = sections[idx]["data"].rename(columns = data.ident.to_dict())

def _rename_main(sections):
    for idx in range(len(sections)):
        sections[idx]["main"] = [
            {main.loc[key, "ident"] if key in main.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["main"]]

def _rename_method(sections):
    for idx in range(len(sections)):
        sections[idx]["method"] = [
            {method.loc[key, "ident"] if key in method.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["method"]]
        
def _rename_values_method_code(sections):
    for section in sections:
        for row in section["main"]:
            if 'method_code' in row:
                code = str(row['method_code'])
                if code in methods.index:
                    row['method_code'] = methods.loc[code, "ident"]

def _rename_values_comments(sections):
    for section in sections:
        if "comments" in section["data"].columns:
            codes = section["data"].comments.fillna(-1).astype(int)
            missing = list(set(codes.unique()) - set(comments.index))
            labels = pd.concat((comments,
                                pd.DataFrame([{"ident": code} for code in missing], index=missing)))
            section["data"]["comments"] = labels.loc[codes, "ident"].values

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


def _dump_line(line):
    return ",".join("%s=%s" % (k,v) for k,v in line.items() if str(v) and (not isinstance(v, float) or not np.isnan(v)))

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
                    f.write(_dump_line(row) + "\n")

def _unrename_blocks(sections):
    for idx in range(len(sections)):
        sections[idx] = {unblocknames.get(name, name): block
                         for name, block in sections[idx].items()}

def _unmake_dfs(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].to_dict('records')

def _unrename_data_columns(sections):
    for idx in range(len(sections)):
        if "data" in sections[idx]:
            sections[idx]["data"] = sections[idx]["data"].rename(columns = undata.code.to_dict())

def _unrename_main(sections):
    for idx in range(len(sections)):
        sections[idx]["main"] = [
            {unmain.loc[key, "code"] if key in unmain.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["main"]]

def _unrename_method(sections):
    for idx in range(len(sections)):
        sections[idx]["method"] = [
            {unmethod.loc[key, "code"] if key in unmethod.index else key: value
             for key, value in row.items()}
            for row in sections[idx]["method"]]
        
def _unrename_values_method_code(sections):
    for section in sections:
        for row in section["main"]:
            if 'method_code' in row:
                code = str(row['method_code'])
                if code in unmethods.index:
                    row['method_code'] = unmethods.loc[code, "code"]

def _unrename_values_comments(sections):
    for section in sections:
        if "comments" in section["data"].columns:
            codes = section["data"].comments
            missing = list(set(codes.unique()) - set(uncomments.index))
            labels = pd.concat((uncomments,
                                pd.DataFrame([{"code": code} for code in missing], index=missing)))
            section["data"]["comments"] = labels.loc[codes, "code"].values
                    
def dump(sections, *arg, **kw):
    sections = copy.deepcopy(sections)    
    _unrename_values_comments(sections)
    _unrename_data_columns(sections)
    _unmake_dfs(sections)
    _unrename_method(sections)
    _unrename_values_method_code(sections)
    _unrename_main(sections)
    _unrename_blocks(sections)
    sections = _dump_raw(sections, *arg, **kw)
    return sections
