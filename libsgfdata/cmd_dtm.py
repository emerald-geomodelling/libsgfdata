import click
from . import dtm
import rasterio

class sample_dtm(object):
    @classmethod
    def decorate(cls, cmd):
        cmd = click.option('--crs', type=int, help="CRS of boreholes")(cmd)
        cmd = click.option('--sample-dtm', type=click.File('rb'), help="Sample a DTM raster. Note: requires crs.")(cmd)
        return cmd

    @classmethod
    def transform(cls, data, crs, sample_dtm, **kw):
        assert crs is not None, "--crs is required for sampling a dtm"
        with rasterio.open(sample_dtm) as f:
            dtm.sample_z_coordinate_from_dtm(data, crs, f, overwrite=True)
        return data
