import pytest
from utils import compare_files

from rompy.swan import SwanModel


@pytest.fixture
def model():
    return SwanModel(
        run_id="test_swan",
        output_dir="simulations",
    )


def test_generate(model):
    model.generate()
    compare_files("simulations/test_swan/INPUT", "simulations/test_swan_ref/INPUT")


def test_swan_input():
    model = SwanModel(
        run_id="test_swan",
        output_dir="simulations",
        template=dict(friction="MAD2"),
    )
    assert model.template.friction == "MAD2"
