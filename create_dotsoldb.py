# Given a CSV file containing lat and lon, create a dotsol
import shutil

from dotsolmaker import DotSolMaker
import pandas as pd
import glob
import os

def merge_all_dot_sol(outputs_dir, dot_sol_output):
    """
    Merge all .SOL into one
    :param outputs_dir: directory containing the dynamic .SOL
    :param dot_sol_output: file to write the content to. This is the static .SOL
    """
    match = f"{outputs_dir}/*.SOLD"
    all_dot_sols = glob.glob(match)
    all_dot_sols.sort()

    with open(dot_sol_output, "wb") as outfile:
        for f in all_dot_sols:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
                outfile.write('\n'.encode())


def create_static_dotsol(lon_lat_file, outputfile):

    if not os.path.exists(lon_lat_file):
        print(f"{lon_lat_file} not found. Exiting...")
        return

    tmp_sold = f"{os.getcwd()}/tmp_sold/"
    os.makedirs(tmp_sold, exist_ok=True)

    df_lon_lat = pd.read_csv(lon_lat_file)
    lon_df = df_lon_lat['lon']
    lat_df = df_lon_lat['lat']
    num_rows = df_lon_lat.shape[0]

    for row_i in range(num_rows):
        lon = lon_df.iloc[row_i]
        lat = lat_df.iloc[row_i]
        dsm = DotSolMaker(lon, lat, fext='SOLD', dotsol_folder=tmp_sold)
        dsm.get_dotsol()

    merge_all_dot_sol(tmp_sold, outputfile)
    shutil.rmtree(tmp_sold, )
    print(f"Created a static .SOL at : {outputfile}\n")



# Example:
working_dir = os.getcwd()

## Update these two variables accordingly:
lon_lat_file = f"{working_dir}/sample_lon_lat.csv"
outputfile = f"{working_dir}/sample_dotsol.SOL"

if __name__ == '__main__':
    create_static_dotsol(lon_lat_file, outputfile)


