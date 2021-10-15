import re
import pkg_resources
import pandas as pd
import numpy as np
import slugify
import dateutil.parser
import datetime
import logging

logger = logging.getLogger(__name__)

blocknames = {"£": "method", "$":"main", "#":"data", "€": "method"}
unblocknames = {v:k for k, v in blocknames.items()}

na_values = ['', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan',
             '1.#IND', '1.#QNAN', '<NA>', 'N/A', 'NULL', 'NaN', 'n/a', 'nan', 'null']

def _read_csv(f):
    return pd.read_csv(f, na_values=na_values, keep_default_na=False).set_index("code").sort_index()

with pkg_resources.resource_stream("libsgfdata", "method.csv") as f:
    method = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "main.csv") as f:
    main = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "data.csv") as f:
    data = _read_csv(f)
block_metadata = {"method": method, "main": main, "data": data}
    
with pkg_resources.resource_stream("libsgfdata", "methods.csv") as f:
    methods = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "comments.csv") as f:
    comments = _read_csv(f)
with pkg_resources.resource_stream("libsgfdata", "data-flags.csv") as f:
    data_flags = _read_csv(f)


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

def _conv_date(v):
    try:
        if len(v) >= 8:
            return dateutil.parser.isoparse(v).date()
    except ValueError as exception:
        logger.debug("Unable to parse date as iso %s: %s" % (v, exception))
    try:
        return dateutil.parser.parse(v, parserinfo=dateutil.parser.parserinfo(dayfirst=True)).date()
    except Exception as e:
        #fixme: make this per file, not per depth row of data
        logger.debug("Unable to parse date %s: %s" %(v,e))
        return v

def _conv_datetime(v):
    try:
        return dateutil.parser.parse(v, parserinfo=dateutil.parser.parserinfo(dayfirst=True))
    except Exception as e:
        logger.debug("Unable to parse time %s: %s" %(v,e))
        return v
    
typemap = pd.DataFrame([
    {"name": np.nan, "conv": np.nan},
    {"name": "date", "conv": _conv_date},
    {"name": "datetime", "conv": _conv_datetime},
    {"name": "time", "conv": np.nan}
]).set_index("name")

for block in block_metadata.values():
    typemapped = typemap.loc[block.type].set_index(block.index)
    for col in typemapped.columns:
        block[col] = typemapped[col]

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

unmethod = method.reset_index().drop_duplicates("ident").set_index("ident")
unmain = main.reset_index().drop_duplicates("ident").set_index("ident")
undata = data.reset_index().drop_duplicates("ident").set_index("ident")
unmethods = methods.reset_index().drop_duplicates("ident").set_index("ident")
uncomments = comments.reset_index().drop_duplicates("ident").set_index("ident")
undata_flags = data_flags.reset_index().drop_duplicates("ident").set_index("ident")
