from __future__ import annotations

import os
from datetime import datetime
from typing import List

from pydantic import BaseModel, validator

from rompy import TEMPLATES_DIR
from rompy.configuration.base import BaseConfig
from rompy.types import Coordinate


class OutputLocs(BaseModel):
    """Output locations for SWAN

    Parameters
    ----------
    coords : List[Coordinate]
        List of coordinates to output spectra
    """

    coords: List[Coordinate] = [["115.61", "-32.618"], ["115.686067", "-32.532381"]]

    def __repr__(self):
        ret = __class__.__name__ + "\n"
        for coord in self.coords:
            ret += f"  {coord[0]} {coord[1]}\n"
        return ret


class SwanConfig(BaseConfig):
    """SWAN configuration

    Parameters
    ----------
    template : str
        Path to template file. If this is a git repository, the template will be cloned by cookiecutter.
    out_start : datetime. If not provided, will be set to compute_start
    out_intvl : str
        Output interval. Must be in the format "1.0 HR" or "1.0 DY"
    output_locs : OutputLocs
        List of coordinates to output spectra
    cgrid : str
        Grid definition for current output
    cgrid_read : str
        Grid definition for current input
    wind_grid : str TODO clean up these definitions
        Grid definition for wind output
    wind_read : str
        Grid definition for wind input
    bottom_grid : str
        Grid definition for bathymetry output
    bottom_file : str
        Path to bathymetry file
    friction : str
        Friction type. Must be one of MAD, OTHER or ANDANOTHER
    friction_coeff : str
        Friction coefficient. Must be between 0 and 1
    spectra_file : str
        Path to input boundary spectra file
    """

    template: str = os.path.join(TEMPLATES_DIR, "swan")
    out_start: datetime | None = None
    out_intvl: str = "1.0 HR"
    output_locs: OutputLocs = OutputLocs()
    cgrid: str = "REG 115.68 -32.76 77 0.39 0.15 389 149"
    cgrid_read: str = ""
    wind_grid: str = "REG 115.3 -32.8 0.0 2 3 0.3515625 0.234375  NONSTATION 20200221.040000  10800.0 S"
    wind_read: str = "SERIES 'extracted.wind' 1 FORMAT '(3F8.1)'"
    bottom_grid: str = "REG 115.68 -32.76 77 390 150 0.001 0.001 EXC -99.0"
    bottom_file: str = "bathy.bot"
    friction: str = "MAD"
    friction_coeff: str = "0.1"
    spectra_file: str = "boundary.spec"

    @validator("out_start", "out_intvl", pre=True)
    def validate_out_start_intvl(cls, v):
        return cls.validate_compute_start_stop(v)

    @validator("friction")
    def validate_friction(cls, v):
        if v not in ["MAD", "OTHER", "ANDANOTHER"]:
            raise ValueError(
                "friction must be one of MAD, OTHER or ANDANOTHER"
            )  # TODO Raf to add actual friction options
        return v

    @validator("friction_coeff")
    def validate_friction_coeff(cls, v):
        # TODO Raf to add sensible friction coeff range
        if float(v) > 1:
            raise ValueError("friction_coeff must be less than 1")
        if float(v) < 0:
            raise ValueError("friction_coeff must be greater than 0")
        return v
