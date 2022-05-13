import math
import os
import subprocess
import pygeohash as pgh
from owslib.wcs import WebCoverageService
from pyproj import Transformer
from osgeo import gdal
import numpy as np
import pandas as pd
from glob import glob
from shutil import copyfile, copyfileobj


class DotSolMaker(object):

    def __init__(self, lon, lat, fext='SOL', dotsol_folder=None):
        self.depth = 600
        self.lat = lat
        self.lon = lon
        self.geohashed = self.geohash_convert(self.lat, self.lon)
        self.crs = 'urn:ogc:def:crs:EPSG::4326'
        self.win_size = 8
        self.layers_aliases = {'bulkdensity': 'bdod', 'clay': 'clay', 'organicsoil': 'soc', 'sandfraction': 'sand'}
        self.url_root = 'http://maps.isric.org/mapserv?map=/map/'
        # availabe depth ranges to download soilgrids layers
        self.depth_ranges = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 100), (100, 200)]  # depth in cm
        self.no_data_value = 255
        self.pwd = os.getcwd()
        self.tmp_folder = f"{self.pwd}/tmp/"
        self.samples_folder = f"{self.pwd}/samples/"
        self.dotsol_folder = f"{self.pwd}/dotsol_outputs/" if dotsol_folder is None else dotsol_folder
        self.dotsolsample = f"{self.samples_folder}sample_asc_{self.geohashed}.csv"
        self.dotsoloutput = f"{self.dotsol_folder}{self.geohashed}.{fext}"
        self.dotsol_exec_path = f"{self.pwd}/exec/dotSolAPI2.exe"
        self.thsol_tmp_path = None

    def get_bounding_box(self, radius_in_m=1000):
        # The data will be at 2km x 2km extent
        # 1 deg = 110,000 m
        lon_rad = self.deg_to_rad(self.lon)
        lat_rad = self.deg_to_rad(self.lat)

        radius = self.get_earth_radius(lat_rad)
        pradius = radius * math.cos(lat_rad)

        lat_min = lat_rad - radius_in_m / radius
        lat_max = lat_rad + radius_in_m / radius
        lon_min = lon_rad - radius_in_m / pradius
        lon_max = lon_rad + radius_in_m / pradius

        bbox_rad = [lon_min, lat_min, lon_max, lat_max]
        return [self.rad_to_deg(val) for val in bbox_rad]

    @staticmethod
    def get_earth_radius(lat):
        wgsa = 6378137.0  # Major semiaxis [m]
        wgsb = 6356752.3  # Minor semiaxis [m]

        an = wgsa * wgsa * math.cos(lat)
        bn = wgsb * wgsb * math.sin(lat)
        ad = wgsa * math.cos(lat)
        bd = wgsb * math.sin(lat)
        return math.sqrt((an * an + bn * bn) / (ad * ad + bd * bd))

    @staticmethod
    def deg_to_rad(degrees):
        return degrees * math.pi / 180

    @staticmethod
    def rad_to_deg(radians):
        return radians * 180 / math.pi

    def normalize_degrees(self, degrees):
        pass

    def from_4326_TO_3857(self, lon, lat):
        TRAN_4326_TO_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
        return TRAN_4326_TO_3857.transform(lon, lat)

    def geohash_convert(self, lat, lon, length=10):
        return pgh.encode(latitude=self.lat, longitude=self.lon, precision=length)

    def download_soilproperty(self, layer, depth_range):
        cover_id = f"{layer}_{depth_range[0]}-{depth_range[1]}cm_mean"
        outname_id = f"{layer}_{depth_range[1] - depth_range[0]}cm_mean"
        outname = f"{self.tmp_folder}{outname_id}.tif"

        url = f"{self.url_root}{layer}.map"
        wcs = WebCoverageService(url, version='1.0.0')

        if cover_id not in wcs.contents.keys():
            print(f"Could not find a layer that matches: {cover_id}")
            return

        bbox = self.get_bounding_box()

        response = wcs.getCoverage(
            identifier=cover_id,
            crs=self.crs,
            bbox=bbox,
            width=self.win_size, height=self.win_size,
            format='GEOTIFF_INT16')

        with open(outname, 'wb') as file:
            file.write(response.read())

        return outname

    def average_raster(self, this_path):
        """
        :param this_path:
        :return: -89 (if all missing data or 255) | mean(array)
        """
        raster_obj = gdal.Open(this_path)
        raster_arr = raster_obj.GetRasterBand(1).ReadAsArray()
        array_1d = raster_arr.reshape(raster_arr.size, )
        array_no_ndv = np.delete(array_1d, np.where(array_1d == self.no_data_value))
        return -89 if array_no_ndv.size == 0 else round(array_no_ndv.mean(), 2)

    def get_soilproperty_data_for_all_depths(self, layer):
        data = list()
        for depth_range in self.depth_ranges:
            this_path = self.download_soilproperty(layer, depth_range)
            if this_path is None:
                val = -99
            else:
                val = self.average_raster(this_path)
            data.append(val)
            print(f"Evaluating {layer} at {depth_range} cm ==> {val}")
        return data

    def get_dotsol_soilprop_sample(self):
        dict_summary = dict()
        for la in sorted(self.layers_aliases.keys()):
            layer = self.layers_aliases.get(la)
            dict_summary[la] = self.get_soilproperty_data_for_all_depths(layer)
        # print(dict_summary)
        # dict_summary = {'bulkdensity': [147.61, 149.2, 149.31, 150.62, 151.78, 153.12],
        #                 'clay': [152.0, 149.3, 165.81, 171.28, 175.36, 174.38],
        #                 'organicsoil': [48.78, 32.42, 29.53, 24.16, 22.39, 26.31],
        #                 'sandfraction': [717.47, 726.42, 712.47, 706.22, 703.72, 710.81]}

        df_summary = pd.DataFrame.from_dict(dict_summary)
        df_summary['bulkdensity'] = round(df_summary['bulkdensity'] / 100, 2)
        df_summary = round(df_summary, 2)
        df_summary['Latitude'] = self.lat
        df_summary['Longitude'] = self.lon
        df_summary['Depth'] = self.depth

        df_summary.to_csv(self.dotsolsample, sep='\t', encoding='utf-8', index=False)

    def compute_pwp(self, clay_val, oc_val, sand_val):
        # Step #1 - convert OC to OM
        om_val = 2 * oc_val
        om_val /= 2  # 1000
        clay_val /= 100
        sand_val /= 100

        # Step #2 - compute theta_1500_t
        theta_1500_t = 0.031 - (0.024 * sand_val) + (0.487 * clay_val) + (0.006 * om_val) \
                       + (0.005 * sand_val * om_val) - (0.013 * clay_val * om_val) + (0.068 * sand_val * clay_val)

        # Step #3 - finally compute theta_1500
        theta_1500 = (1.14 * theta_1500_t) - 0.02

        return round(theta_1500, 2)

    def compute_fc_row(self, col):
        clay_val = col['clay']
        oc_val = col['organicsoil']
        sand_val = col['sandfraction']

        return self.compute_field_capacity(clay_val, oc_val, sand_val)

    def compute_field_capacity(self, clay_val, oc_val, sand_val):
        """
        Calculate Field Capacity based on Clay, Organic Matter and sand value
        :param clay_val: percentage of clay
        :param oc_val: percentage of organic carbon
        :param sand_val: percentage of sand
        :return: a float value representing FC
        """

        # Step #1 - convert OC to OM
        om_val = 2 * oc_val
        om_val /= 2  # 1000
        clay_val /= 100
        sand_val /= 100

        # Step #2 - compute theta_33_t
        theta_33_t = 0.299 - (0.251 * sand_val) + (0.195 * clay_val) + (0.011 * om_val) \
                     + (0.006 * sand_val * om_val) - (0.027 * clay_val * om_val) + (0.452 * sand_val * clay_val)

        # Step #3 - compute actual F.C: theta_33
        theta_33 = theta_33_t + ((1.283 * theta_33_t * theta_33_t) - (0.374 * theta_33_t) - 0.015)

        return round(theta_33, 2)

    def clean_tmp_folder(self):
        files_to_del = glob(f"{self.tmp_folder}/*.tif")
        for f in files_to_del:
            os.remove(f)
        return len(files_to_del) == 0

    def run_dotsol_exec(self):
        if not os.path.exists(self.dotsol_exec_path):
            print("dotSolAPI2.exe not found")
            return
        if not os.path.exists(self.dotsolsample):
            print("dotsol sample file not found")
            return

        args_run = [self.dotsol_exec_path, self.dotsolsample]
        subprocess.call(args_run, stdout=subprocess.DEVNULL)
        self.thsol_tmp_path = glob(f"{self.pwd}/*.SOL")[0]

    def update_dotsol_code(self):
        """
        The dynamic .SOL has a hardcoded codename (e.g. TH_00001). We need to change that
        :param geohash_code: new code to substitute
        :param sol_file: the file to correct
        :return:
        """
        sol_file = self.thsol_tmp_path
        from_file = open(sol_file)
        hline = from_file.readline()
        hline_new = "*" + self.geohashed + hline[12:]
        with open(sol_file, mode="w") as to_file:
            to_file.write(hline_new)
            copyfileobj(from_file, to_file)
        from_file.close()

    def rename_dotsol_file(self):
        if os.path.exists(self.thsol_tmp_path) and not os.path.exists(self.dotsoloutput):
            os.rename(self.thsol_tmp_path, self.dotsoloutput)

    def get_dotsol(self):
        self.get_dotsol_soilprop_sample()
        self.run_dotsol_exec()
        if self.thsol_tmp_path is None:
            print("Could not generate dotsol file")

        self.update_dotsol_code()
        self.rename_dotsol_file()
        self.clean_tmp_folder()
        os.remove(self.dotsolsample)
        print(
            f"Created a .SOL for (lon: {self.lon}, lat:{self.lat}) with geohashed value: {self.geohashed} at: {self.dotsoloutput}")


## Test
# b = DotSolMaker(lon=-15.657, lat=16.107, fext='SOLD')
# b.get_dotsol()
