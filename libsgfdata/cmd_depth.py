import click
import numpy as np

class cmd_depth(object):
    @classmethod
    def decorate(cls, cmd):
        cmd = click.option(
            '--depth', type=int, help="Normalize depth to positive (1) or negative(-1)"
        )(cmd)
        return cmd

    @classmethod
    def transform(cls, data, depth, **kw):
        for section in data:
            if "data" in section:
                for col in ("depth", "start_depth", "end_depth"):
                    if col in section["data"].columns:
                        section["data"][col] = np.abs(section["data"][col]) * depth
        return data
