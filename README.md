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

# Command line usage

`libsgfdata` optionally comes with a command line tool `sgfdata`. This
is installed with `pip install libsgfdata[cmd]`, and provides command
line access to file format conversion, normalization, dtm raster
sampling of z coordinates and more. See `sgfdata --help` for more
information on this.

Support for other file formats and online services must be installed separately, see e.g. [libgeosuiteprv](https://github.com/emerald-geomodelling/libgeosuiteprv), [libgeosuitesnd](https://github.com/emerald-geomodelling/libgeosuitesnd) and [libnadagclient](https://github.com/emerald-geomodelling/libnadagclient).

# Library usage

See the [example usage notebook](docs/Example%20usage.ipynb) for details.
