from pathlib import Path
import pytest
from utils import compare_files

from rompy.model import ModelRun
from rompy.swan import SwanConfig, SwanGrid

here = Path(__file__).parent


@pytest.fixture
def grid():
    return SwanGrid(x0=115.68, y0=-32.76, dx=0.001, dy=0.001, nx=390, ny=150, rot=77)


@pytest.fixture
def model(tmpdir):
    return ModelRun(
        run_id="test_swan",
        output_dir=str(tmpdir),
    )


@pytest.fixture
def nesting(tmpdir):
    return ModelRun(
        run_id="test_nesting",
        output_dir=str(tmpdir),
        config=SwanConfig(
            subnests=[
                SwanConfig(),
                SwanConfig(subnests=[SwanConfig()]),
            ]
        ),
    )


@pytest.mark.skip(reason="Overlap here with swan temlate tests - need to consolidate")
def test_generate(tmpdir, model):
    model.config.write(
        ModelRun(
            run_id="test_swan",
            output_dir=str(tmpdir),
        )
    )
    compare_files(
        tmpdir / model.run_id / "INPUT",
        here / "simulations/test_swan_ref/INPUT",
    )


def test_swan_input(tmpdir, grid):
    model = ModelRun(
        run_id="test_swan",
        output_dir=str(tmpdir),
        config=SwanConfig(grid=grid, physics=dict(friction="MAD")),
    )
    assert model.config.physics.friction == "MAD"


def test_failing_friction(tmpdir):
    with pytest.raises(ValueError):
        model = ModelRun(
            run_id="test_swan",
            output_dir=str(tmpdir),
            config=dict(friction="BAD", model_type="swan"),
        )


@pytest.mark.skip(reason="not working, need to investigate")
def test_nesting(nesting):
    nesting.generate()
    # compare_files(
    #     os.path.join(here, "simulations/test_swan/INPUT"),
    #     os.path.join(here, "simulations/test_swan_ref/INPUT"),
    # )
