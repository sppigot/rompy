import os

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
        os.path.join(here, "simulations/test_base/INPUT"),
        os.path.join(here, "simulations/test_base_ref/INPUT"),
    )


def test_swan_input():
    model = SwanModel(
        run_id="test_swan",
        output_dir="simulations",
        template=dict(friction="MAD2"),
    )
    assert model.template.friction == "MAD2"
