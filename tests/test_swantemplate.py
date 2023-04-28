import os
import shutil
import tempfile
from datetime import datetime

import pytest
import xarray as xr
from utils import compare_files

from rompy.core import TimeRange
from rompy.swan import SwanConfig, SwanDataGrid, SwanGrid, SwanModel

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def config():
    """Create a SwanConfig object."""
    return SwanConfig()


def test_swantemplate(config):
    """Test the swantemplate function."""
    time = TimeRange(start=datetime(2020, 2, 21, 4), end=datetime(2020, 2, 24, 4))
    runtime = SwanModel(run_id="test_swantemplate", output_dir="simulations")
    config.write(runtime=runtime)
    compare_files(
        os.path.join(here, "simulations/test_swan_ref/INPUT"),
        os.path.join(here, "simulations/test_swantemplate/INPUT"),
    )
    shutil.rmtree(os.path.join(here, "simulations/test_swantemplate"))
