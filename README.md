# Parser for Swedish Geotechnical Society data format

Parser for data from geotechnical field investigations in the data
format specified in Report 3:2012E from the Swedish Geotechnical
Society. This includes TOT and CPT files, used by e.g.
[NADAG](http://geo.ngu.no/kart/nadag/).

See [their report
portal](http://www.sgf.net/web/page.aspx?refid=2678) for how to
download this report.

# Usage

    >>> import libsgfdata
    >>> sections = libsgfdata.parse("example.tot")
    
    >>> sections[0]["main"][0]
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

Note that the main block of a section is a list of rows, while in practice it is very uncommon for this list to have any other length than 1.
