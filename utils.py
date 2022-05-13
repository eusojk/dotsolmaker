from pyproj import Transformer


def from_4326_TO_3857(lon, lat):
    tran_4326_to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    return tran_4326_to_3857.transform(lon, lat)





