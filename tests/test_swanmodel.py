import os
import shutil

import pytest
from utils import compare_files

from rompy.swan import SwanConfig, SwanModel

here = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def model():
    return SwanModel(
        run_id="test_swan",
        output_dir=os.path.join(here, "simulations"),
    )


@pytest.fixture
def nesting():
    return SwanModel(
        run_id="test_nesting",
        output_dir=os.path.join(here, "simulations"),
        config=SwanConfig(subnests=[SwanConfig(), SwanConfig(subnests=[SwanConfig()])]),
    )


def test_generate(model):
    model.config.generate(SwanModel(run_id="test_swan", output_dir="simulations"))
    compare_files(
        os.path.join(here, "simulations/test_swan/INPUT"),
        os.path.join(here, "simulations/test_swan_ref/INPUT"),
    )
    # shutil.rmtree(os.path.join(here, "simulations/test_swan"))


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


@pytest.mark.skip(reason="not working, need to investigate")
def test_nesting(nesting):
    nesting.generate()
    # compare_files(
    #     os.path.join(here, "simulations/test_swan/INPUT"),
    #     os.path.join(here, "simulations/test_swan_ref/INPUT"),
    # )
    # shutil.rmtree(os.path.join(here, "simulations/test_swan"))
