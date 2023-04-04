import os
import shutil

import pytest
from utils import compare_files

from rompy.swan import SwanModel

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def model():
    return SwanModel(
        run_id="test_swan",
        output_dir=os.path.join(here, "simulations"),
    )


def test_generate(model):
    model.generate()
    compare_files(
        os.path.join(here, "simulations/test_swan/INPUT"),
        os.path.join(here, "simulations/test_swan_ref/INPUT"),
    )
    shutil.rmtree(os.path.join(here, "simulations/test_swan"))


def test_swan_input():
    model = SwanModel(
        run_id="test_swan",
        output_dir="simulations",
        config=dict(friction="MAD"),
    )
    assert model.config.friction == "MAD"


def test_failing_friction():
    with pytest.raises(ValueError):
        model = SwanModel(
            run_id="test_swan",
            output_dir="simulations",
            config=dict(friction="BAD"),
        )
