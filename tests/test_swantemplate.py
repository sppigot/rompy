import os
import shutil
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import xarray as xr
from utils import compare_files

from rompy.core import TimeRange
from rompy.swan import SwanConfig, SwanDataGrid, SwanGrid, SwanModel

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def nc_bathy():
    # touch temp netcdf file
    bottom = SwanGrid(
        x0=115.68, y0=-32.76, rot=77, nx=391, ny=151, dx=0.001, dy=0.001, exc=-99.0
    )
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "bathy.nc")
    # calculate lat/lon manually due to rounding errors in arange
    lat = []
    for nn in range(bottom.ny):
        lat.append(bottom.y0 + (nn * bottom.dy))
    lon = []
    for nn in range(bottom.nx):
        lon.append(bottom.x0 + (nn * bottom.dx))
    ds = xr.Dataset(
        {
            "depth": xr.DataArray(
                np.random.rand(bottom.ny, bottom.nx),
                dims=["lat", "lon"],
                coords={"lat": lat, "lon": lon},
            ),
        }
    )
    ds.to_netcdf(source)
    return SwanDataGrid(
        id="bottom", path=source, z1="depth", var="BOTTOM", latname="lat", lonname="lon"
    )


@pytest.fixture
def nc_data_source():
    # touch temp netcdf file
    # setup to replicate what was already there in the model templates
    wind_grid = SwanGrid(
        x0=115.68, y0=-32.76, rot=77, nx=391, ny=151, dx=0.001, dy=0.001, exc=-99.0
    )
    tmp_path = tempfile.mkdtemp()
    source = os.path.join(tmp_path, "wind_input.nc")

    # calculate lat/lon manually due to rounding errors in arange
    lat = []
    for nn in range(wind_grid.ny):
        lat.append(wind_grid.y0 + (nn * wind_grid.dy))
    lon = []
    for nn in range(wind_grid.nx):
        lon.append(wind_grid.x0 + (nn * wind_grid.dx))

    ds = xr.Dataset(
        {
            "u": xr.DataArray(
                np.random.rand(10, wind_grid.ny, wind_grid.nx),
                dims=["time", "latitude", "longitude"],
                coords={
                    "time": pd.date_range("2000-01-01", periods=10),
                    "latitude": lat,
                    "longitude": lon,
                },
            ),
            "v": xr.DataArray(
                np.random.rand(10, wind_grid.ny, wind_grid.nx),
                dims=["time", "latitude", "longitude"],
                coords={
                    "time": pd.date_range("2020-02-21", periods=10),
                    "latitude": lat,
                    "longitude": lon,
                },
            ),
        }
    )
    ds.to_netcdf(source)
    return SwanDataGrid(id="wind", var="WIND", path=source, z1="u", z2="v")


@pytest.fixture
def config(nc_data_source, nc_bathy):
    """Create a SwanConfig object."""
    # return SwanConfig(forcing={"wind": nc_data_source, "bottom": nc_bathy})
    return SwanConfig(forcing={"bottom": nc_bathy, "wind": nc_data_source})


def test_swantemplate(config):
    """Test the swantemplate function."""
    time = TimeRange(start=datetime(2020, 2, 21, 4), end=datetime(2020, 2, 24, 4))
    runtime = SwanModel(
        run_id="test_swantemplate",
        output_dir=os.path.join(here, "simulations"),
        config=config,
    )
    runtime.generate()
    compare_files(
        os.path.join(here, "simulations/test_swan_ref/INPUT_NEW"),
        os.path.join(here, "simulations/test_swantemplate/INPUT"),
    )
    shutil.rmtree(os.path.join(here, "simulations/test_swantemplate"))
