#!/usr/bin/env python

import setuptools
import os

setuptools.setup(
    name='libsgfdata',
    version='0.0.13',
    description='Parser for Swedish Geotechnical Society data format',
    long_description="""Parser for data from geotechnical field
    investigations in the data format specified in Report 3:2012E from
    the Swedish Geotechnical Society, see
    http://www.sgf.net/web/page.aspx?refid=2678 for how to download
    this report.""",
    long_description_content_type="text/markdown",
    author='Egil Moeller',
    author_email='em@emeraldgeo.no',
    url='https://github.com/emerald-geomodelling/libsgfdata',
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={'libsgfdata': ['*/*.csv']},
    install_requires=[
        "numpy",
        "pandas",
        "python-slugify",
        "python-dateutil",
        "cchardet"
    ],
    extras_require = {
        "cmd":  [
            "click"
        ],
        "dtm": [
            "pyproj",
            "rasterio"
        ],
    },

    entry_points = {
        'libsgfdata.parsers': ['sgf=libsgfdata.parser:parse'],
        'libsgfdata.dumpers': ['sgf=libsgfdata.dumper:dump'],
        'libsgfdata.transforms': ['sample_dtm=libsgfdata.cmd_dtm:sample_dtm',
                                  'normalize=libsgfdata.cmd_normalize:cmd_normalize',
                                  'depth=libsgfdata.cmd_depth:cmd_depth',
                                  'depth_to_material=libsgfdata.cmd_depth_to_material:depth_to_material'
        ],
        'console_scripts': ['sgfdata=libsgfdata.cmd:main'],
    }
)
