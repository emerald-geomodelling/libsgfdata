import pyproj
import rasterio

def project(innproj, utproj, xinn, yinn):
    innproj = int(innproj)
    utproj = int(utproj)
    #UTM convention is coordinate order Northing-Easting. CCh, 2020-06-18
    return pyproj.Transformer.from_crs(innproj, utproj, always_xy=True).transform(xinn, yinn)

def sample_z_coordinate_from_dtm(sections, crs, raster, overwrite=True):
    """Sample z coordinate for boreholes from a DTM raster. If overwrite
    is false, only add z-coordinate if it is missing."""
    
    if isinstance(raster, str):
        with rasterio.open(dtm) as f:
            _sample_z_coordinate_from_dtm(sections, crs, f, overwrite)
    else:
        _sample_z_coordinate_from_dtm(sections, crs, raster, overwrite)
    
def _sample_z_coordinate_from_dtm(sections, crs, raster, overwrite):
    raster_crs = raster.crs.to_epsg()
    for section in sections:
        if "main" not in section or not len(section["main"]):
            continue
        if not overwrite and "z_coordinate" in section["main"][0]:
            continue
        if "x_coordinate" not in section["main"][0] or "y_coordinate" not in section["main"][0]:
            continue
        x, y = project(crs, raster_crs,
                       section["main"][0]["x_coordinate"],
                       section["main"][0]["y_coordinate"])
        section["main"][0]["z_coordinate"] = next(iter(raster.sample([(x, y)])))[0]
 
