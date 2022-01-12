import click
import re
import numpy as np

class depth_to_material(object):
    @classmethod
    def decorate(cls, cmd):
        cmd = click.option('--depth-to-material', type=str, multiple=True, help="Set depth_bedrock to shallowest depth labeled with a certain material name in the comment (multiple can be given)")(cmd)
        cmd = click.option('--material-column', type=str, default="comments", help="Column to get material types from (comments)")(cmd)
        return cmd

    @classmethod
    def transform(cls, data, depth_to_material, material_column, **kw):
        for section in data:
            borehole_data = section["data"]

            def find_material(comment):
                for material in depth_to_material:
                    if re.search(r"(^|[^_a-zA-Z])%s([^_a-zA-Z]|$)" % material, comment):
                        return material
                return None

            materials = borehole_data[material_column].apply(find_material)

            depth_bedrock = np.NaN
            for cls in depth_to_material:
                if np.isnan(depth_bedrock):
                    depth_bedrock = borehole_data.loc[
                        materials == cls, "start_depth"].abs().min()
            if not np.isnan(depth_bedrock):
                section["main"][0]["depth_bedrock"] = depth_bedrock
                section["main"][0]["stop_code"] = "stop_against_presumed_rock"

        return data
