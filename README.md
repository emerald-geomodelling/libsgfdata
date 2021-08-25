# Parser for Swedish Geotechnical Society data format

Parser for data from geotechnical field investigations in the data
format specified in Report 3:2012E from the Swedish Geotechnical
Society. This includes TOT and CPT files, used by e.g.
[NADAG](http://geo.ngu.no/kart/nadag/).

See [their report
portal](http://www.sgf.net/web/page.aspx?refid=2678) for how to
download this report.

Additionally fields / extensions from [Geotech
AB](https://static1.squarespace.com/static/565c5cc1e4b05079e4c0fcfb/t/587c984bbf629abac09d265f/1484560476906/6-SWE-CPT-LOG-v5.xx.pdf)
are supported.

# Usage

    >>> import libsgfdata
    >>> data = libsgfdata.parse("example.tot")
    
    >>> data[0]["main"][0]
    {'pre_drilling_depth': '',
     'method_code': 'norwegian_total_sounding',
     'work_or_project_number': '12345678-01',
     'investigation_point': 1001,
     'signature': 'J. Random Engineer'}
     
     >>> data[0]["data"].head()
       depth  feed_trust_force   load  point_of_time  AKZ  ...  flush_pressure   SP  flush_rate  comments    T
    0  0.025   -0.021          -0.027   154908        617  ...    0.451         0.0      0.0     no_c...   NaN
    1  0.050    0.231           0.135   154908        621  ...    0.298         0.0      0.0     no_c...   NaN
    2  0.075    0.430           0.334   154909        637  ...    0.376         0.0      0.0     no_c...   NaN
    3  0.100    0.478           0.488   154909        641  ...    0.377         0.0      0.0     no_c...   NaN
    4  0.125    0.500           0.500   154910        657  ...    0.251         0.0      0.0     no_c...   NaN

Note that the main block of a section is a list of rows, while in
practice it is very uncommon for this list to have any other length
than 1.

To write the data structure back to a file

    >>> with open("example-out.tot", "wb") as f:
        libsgfdata.dump(data, f)

or

    >>> libsgfdata.dump(data, "example-out.tot")

# Character encoding

While the SGF standard clearly says that files should be encoded using `latin-1`, this is often not true in practice. In particular a lot of files found in the wild have been edited by hand in e.g. Notepad on Windows. We try to auto-detect encoding usning [cchardet](https://github.com/PyYoshi/cChardet), and default to `latin-1` if the detection is less than 85% certain. This sometimes fails though. To solve this, you can supply the correct encoding:

    >>> data = libsgfdata.parse("example.tot", "iso-8859-15")

Note that it is unlikely that a failed detection leads to a failure to parse the file: Most common confusions are between different `latin-` charsets, and using the wrong one of these will only lead to non-ascii characters in text fields being wrong, not the entire file failing to read.
