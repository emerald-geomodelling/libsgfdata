import click
from . import normalizer

class cmd_normalize(object):
    @classmethod
    def decorate(cls, cmd):
        cmd = click.option(
            '--normalize', is_flag=True, help="Normalize non-standard extensions to the SGF data format, such as the Geotech AB extension"
        )(cmd)
        return cmd

    @classmethod
    def transform(cls, data, **kw):
        normalizer.normalize(data)
        return data
