import os
import shutil
from datetime import datetime

import pytest
from utils import compare_files

from rompy.core import DateTimeRange
from rompy.swan.config import SwanConfig

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def config():
    """Create a SwanConfig object."""
    return SwanConfig()


def test_swantemplate(config):
    """Test the swantemplate function."""
    time = DateTimeRange(
        start_date=datetime(2020, 2, 21, 4), end_date=datetime(2020, 2, 24, 4)
    )
    config.write(
        run_dir="simulations/test_swantemplate",
        time=time,
    )
    compare_files(
        os.path.join(here, "simulations/test_swan_ref/INPUT"),
        os.path.join(here, "simulations/test_swantemplate/INPUT"),
    )
    shutil.rmtree(os.path.join(here, "simulations/test_swantemplate"))
