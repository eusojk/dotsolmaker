# Dot Sol Maker

## 1. Cloning the project and installing packages
```
git clone https://github.com/eusojk/dotsolmaker
conda create --name dotsolmaker-env python=3.7
conda activate dotsolmaker-env
conda install -c conda-forge gdal
pip install requirements.txt
```

## 2. Provide two required input & output paths in `create_dotsoldb.py`:

```commandline
## Update these two variables accordingly:
lon_lat_file = f"{working_dir}/sample_lon_lat.csv"
outputfile = f"{working_dir}/sample_dotsol.SOL"
```

Here, input is `sample_lon_lat.csv` as it contains lon and lat columns and values of area of study
And the output file has been name `sample_dotsol.SOL`: This file will contain the final .SOL

## 3. Run `create_dotsoldb.py`

