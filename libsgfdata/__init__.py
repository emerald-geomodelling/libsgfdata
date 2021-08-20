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
logger = logging.getLogger(__name__)

blocknames = {"£": "method", "$":"main", "#":"data", "€": "method"}
unblocknames = {v:k for k, v in blocknames.items()}

date_fields = ["HD", "RefDatum"]
datetime_fields = ["AK", "DatumTid"]
time_fields = ["%", "AD"]

na_values = ['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
             '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NULL', 'NaN', 'n/a', 'nan', 'null']

def _read_csv(f):
    return pd.read_csv(f, na_values=na_values, keep_default_na=False).set_index("code")

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
with pkg_resources.resource_stream("libsgfdata", "data-flags.csv") as f:
    data_flags = _read_csv(f)


def make_idents(tbl):
    """Basically we just slugify the name, but for duplicate names, we
    include the unit too to disambiguate.
    """
    duplicates = []
    if "unit" in tbl.columns:
        unit_counts = tbl[["name", "unit"]].fillna(-1).value_counts()
        counts = tbl["name"].value_counts()
        duplicates = counts.loc[counts > 1].index
    def ident_for_row(row):
        name = str(row["name"])
        if row["name"] in duplicates and len(unit_counts[row["name"]]) > 1:
            unit = row["unit"]
            if unit == "0=off 1=on":
                unit = "flag"
            name = "%s-%s" % (name, unit)
        return slugify.slugify(name, separator="_")
    tbl["ident"] = tbl.apply(ident_for_row, axis=1)

make_idents(method)
make_idents(main)
make_idents(data)
make_idents(methods)
make_idents(comments)
make_idents(data_flags)

unmethod = method.reset_index().set_index("ident")
unmain = main.reset_index().set_index("ident")
undata = data.reset_index().set_index("ident")
unmethods = methods.reset_index().set_index("ident")
uncomments = comments.reset_index().set_index("ident")
undata_flags = data_flags.reset_index().set_index("ident")

_RE_FLOAT = re.compile(r"^\s*[-+]?[0-9]*(\.[0-9]*)?([eE][-+]?[0-9]+)?\s*$")
_RE_INT = re.compile(r"^\s*[-+]?[0-9]+\s*$")
# Fields are generally separated by "," and contain a single "="
# separating the key from the value. However, some fields have values
# containing ",", with no quoting. To handle this, we require the key
# to contain only a-z and A-Z. In addition, the Geotech AB extension,
# have date fields (key "%") with no "=" separating the key from the
# value...
_RE_FIELD_SEP = re.compile(r",(?:(?=[a-zA-Z])|(?=%))")

def _conv(k, v):
    # The SGF standard requires specific date formats, but in practice
    # many different formats are in use. We therefore use dateutil to
    # auto-detect the format as well as we can.
    #
    # Examples:
    #
    # AK=200208221132
    # HD=20120105
    # HD=09/04/99
    # HD=27.06.2014
    #
    # We give preference to the norwegian date format over the american one, as this is a scandinavian
    # file format.
    # But seriously, why don't we all just use the ISO format?

    if k in date_fields:
        try:
            return dateutil.parser.parse(v, parserinfo=dateutil.parser.parserinfo(dayfirst=True)).date()
        except Exception as e:
            #fixme: make this per file, not per depth row of data
            logger.debug("Unable to parse date %s: %s" %(v,e))
            return v
    elif k in datetime_fields:
        try:
            return dateutil.parser.parse(v, parserinfo=dateutil.parser.parserinfo(dayfirst=True))
        except Exception as e:
            logger.debug("Unable to parse time %s: %s" %(v,e))
            return v
    elif v and re.match(_RE_INT, v):
        return int(v)
    elif v and re.match(_RE_FLOAT, v):
        return float(v)
    return v

def _parse_line(line):
    try:
        return {k:_conv(k, v) for k, v in (i.split("=", 1) if "=" in i else [i[0], i[1:]] for i in re.split(_RE_FIELD_SEP, line))}
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
            def convert(x):
                try:
                    return int(x)
                except:
                    return x
            codes = section["data"].comments.fillna(-1).apply(convert)
            missing = list(set(codes.unique()) - set(comments.index))
            labels = pd.concat((comments,
                                pd.DataFrame([{"ident": code} for code in missing], index=missing)))
            section["data"]["comments"] = labels.loc[codes, "ident"].values

def _rename_values_data_flags(sections):
    key = "allocated_value_during_performance_of_sounding"
    for section in sections:
        if key in section["data"].columns:
            codes = section["data"][key].fillna(-1).astype(int)
            missing = list(set(codes.unique()) - set(data_flags.index))
            labels = pd.concat((data_flags,
                                pd.DataFrame([{"ident": code} for code in missing], index=missing)))
            section["data"][key] = labels.loc[codes, "ident"].values
            
def parse(*arg, **kw):
    sections = _parse_raw(*arg, **kw)
    _rename_blocks(sections)
    _rename_main(sections)
    _rename_values_method_code(sections)
    _rename_method(sections)
    _make_dfs(sections)
    _rename_data_columns(sections)
    _rename_values_comments(sections)
    _rename_values_data_flags(sections)
    return sections

def _unconv(k, v):
    if k == "DatumTid":
        return v.strftime("%Y%m%d%H%M%S%f")[:-3] # Milliseconds are not supported by strftime, so use %f and remove three decimals
    elif isinstance(v, datetime.date):
        return v.strftime("%Y%m%d")
    elif isinstance(v, datetime.datetime):
        return v.strftime("%Y%m%d%H%M")
    else:
        return str(v)

def _dump_line(line):
    return ",".join("%s=%s" % (k,_unconv(k, v)) for k,v in line.items() if str(v) and (not isinstance(v, float) or not np.isnan(v)))

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
        if "method" not in sections[idx]:
            continue
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
    key = "comments"
    for section in sections:
        if key in section["data"].columns:
            codes = section["data"][key]
            missing = list(set(codes.unique()) - set(uncomments.index))
            labels = pd.concat((uncomments,
                                pd.DataFrame([{"code": code} for code in missing], index=missing)))
            section["data"][key] = labels.loc[codes, "code"].values

def _unrename_values_data_flags(sections):
    key = "allocated_value_during_performance_of_sounding"
    for section in sections:
        if key in section["data"].columns:
            codes = section["data"][key]
            missing = list(set(codes.unique()) - set(undata_flags.index))
            labels = pd.concat((undata_flags,
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
