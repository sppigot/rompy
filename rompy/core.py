# -----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------

import glob
import inspect
import json
import logging
import os
import platform
import zipfile as zf
from datetime import datetime

import cookiecutter.config as cc_config
import cookiecutter.generate as cc_generate
import cookiecutter.repository as cc_repository
import numpy as np
from pydantic import BaseModel
from pydantic import BaseModel as pyBaseModel
from pydantic import PrivateAttr, validator
from pydantic_numpy import NDArray
from shapely.geometry import Polygon

from rompy.configurations.base import BaseConfig

from .types import Bbox
from .utils import json_serial

# pydantic interface to BaseNumericalModel
# https://pydantic-docs.helpmanual.io/usage/models/

# comment using numpy style docstrings

logger = logging.getLogger(__name__)


class BaseModel(pyBaseModel):
    """A base class for all models

    Parameters
    ----------

    run_id : str
        The run id
    compute_start : datetime
        The start time of the simulation
    compute_interval : str
        The time interval of the simulation
    compute_stop : datetime
        The stop time of the simulation
    output_dir : str
        The output directory
    config : BaseConfig
        The configuration object
    """

    run_id: str = "run_id"
    compute_start: datetime = datetime(2020, 2, 21, 4)
    compute_interval: str = "0.25 HR"
    compute_stop: datetime = datetime(2020, 2, 24, 4)
    output_dir: str = "simulations"
    config: BaseConfig = BaseConfig()
    _model: str | None = None

    class Config:
        underscore_attrs_are_private = True

    @validator("compute_start", "compute_stop", pre=True)
    def validate_compute_start_stop(cls, v):
        if isinstance(v, datetime):
            return v
        for fmt in [
            "%Y%m%d.%H%M%S",
            "%Y%m%d.%H%M",
            "%Y%m%dT%H%M%S",
            "%Y%m%dT%H%M",
            "%Y%m%dT%H",
            "%Y%m%dT",
            "%Y-%m-%dT%H%M",
            "%Y-%m-%dT%H",
            "%Y-%m-%dT",
        ]:
            try:
                ret = datetime.strptime(v, fmt)
                return ret
            except ValueError:
                pass
        return v

    @property
    def staging_dir(self):
        """The directory where the model is staged for execution

        returns
        -------
        staging_dir : str
        """

        return os.path.join(self.output_dir, self.run_id)

    @property
    def grid(self) -> "core.Grid":
        """The grid used by the model

        returns
        -------
        grid : core.Grid
        """
        return self._get_grid()

    def _get_grid(self):
        """Subclasses should return an instance of core.Grid"""
        raise NotImplementedError

    def save_settings(self) -> str:
        """Save the run settings

        returns
        -------
        settingsfile : str
        """
        settingsfile = os.path.join(self.staging_dir, "settings.json")
        with open(settingsfile, "w") as f:
            f.write(self.json())
        return settingsfile

    @classmethod
    def load_settings(fn):
        """Load the run settings from a file"""
        with open(fn) as f:
            defaults = json.load(f)

    def generate(self) -> str:
        """Generate the model input files

        returns
        -------
        staging_dir : str
        """
        config_dict = cc_config.get_user_config(
            config_file=None,
            default_config=False,
        )

        repo_dir, cleanup = cc_repository.determine_repo_dir(
            template=self.config.template,
            abbreviations=config_dict["abbreviations"],
            clone_to_dir=config_dict["cookiecutters_dir"],
            checkout=self.config.checkout,
            no_input=True,
        )

        cc_full = {}
        cc_full["cookiecutter"] = self.dict()
        cc_full["cookiecutter"].update(self.config.dict())
        cc_full["cookiecutter"].update({"_template": repo_dir})
        cc_full["cookiecutter"].update({"_generated_at": str(datetime.utcnow())})
        cc_full["cookiecutter"].update({"_generated_by": os.environ.get("USER")})
        cc_full["cookiecutter"].update({"_generated_on": platform.node()})
        cc_full["cookiecutter"].update({"_datefmt": self.config._datefmt})

        staging_dir = cc_generate.generate_files(
            repo_dir=repo_dir,
            context=cc_full,
            overwrite_if_exists=True,
            output_dir=self.output_dir,
        )
        logger.info(f"Successfully generated project in {self.output_dir}")
        return staging_dir

    def zip(self) -> str:
        """Zip the input files for the model run

        This function zips the input files for the model run and returns the
        name of the zip file. It also cleans up the staging directory leaving
        only the settings.json file that can be used to repoducte the run.

        returns
        -------
        zip_fn : str
        """

        # Always remove previous zips
        zip_fn = self.staging_dir + "/simulation.zip"
        if os.path.exists(zip_fn):
            os.remove(zip_fn)

        # Zip the input files
        run_files = glob.glob(self.staging_dir + "/**/*", recursive=True)
        with zf.ZipFile(zip_fn, mode="w", compression=zf.ZIP_DEFLATED) as z:
            for f in run_files:
                z.write(f, f.replace(self.staging_dir, ""))  # strip off the path prefix

        # Clean up run files leaving the settings.json
        for f in run_files:
            if not os.path.basename(f) == "settings.json":
                if os.path.isfile(f):
                    os.remove(f)

        # Clean up any directories
        for f in run_files:
            if os.path.isdir(f):
                os.rmdir(f)

        return zip_fn


class BaseGrid(pyBaseModel):
    """An object which provides an abstract representation of a grid in some geographic space

    This is the base class for all Grid objects. The minimum representation of a grid are two
    NumPy array's representing the vertices or nodes of some structured or unstructured grid,
    its bounding box and a boundary polygon. No knowledge of the grid connectivity is expected.

    """

    x: NDArray
    y: NDArray

    @property
    def minx(self) -> float:
        return np.nanmin(self.x)

    @property
    def maxx(self) -> float:
        return np.nanmax(self.x)

    @property
    def miny(self) -> float:
        return np.nanmin(self.y)

    @property
    def maxy(self) -> float:
        return np.nanmax(self.y)

    def bbox(self, buffer=0.0) -> Bbox:
        """Returns a bounding box for the spatial grid

        This function returns a list [ll_x, ll_y, ur_x, ur_y]
        where ll_x, ll_y (ur_x, ur_y) are the lower left (upper right)
        x and y coordinates bounding box of the model domain

        """
        ll_x = self.minx - buffer
        ll_y = self.miny - buffer
        ur_x = self.maxx + buffer
        ur_y = self.maxy + buffer
        bbox = [ll_x, ll_y, ur_x, ur_y]
        return bbox

    def _get_boundary(self, tolerance=0.2) -> Polygon:
        from shapely.geometry import MultiPoint

        xys = list(zip(self.x.flatten(), self.y.flatten()))
        polygon = MultiPoint(xys).convex_hull
        polygon = polygon.simplify(tolerance=tolerance)

        return polygon

    def boundary(self, tolerance=0.2):
        """
        Returns a boundary polygon as a Shapely Polygon object. Sub-classes can override the private method Grid._get_boundary() but must return a Shapely polygon object.

        Parameters
        ----------
        tolerance : float
            See https://shapely.readthedocs.io/en/stable/manual.html#object.simplify

        Returns
        -------
        polygon : shapely.Polygon see https://shapely.readthedocs.io/en/stable/manual.html#Polygon

        """
        return self._get_boundary(tolerance=tolerance)

    def boundary_points(self, tolerance=0.2):
        """
        Convenience function to convert boundary Shapely Polygon
        to arrays of coordinates

        Parameters
        ----------
        tolerance : float
            Passed to Grid.boundary
            See https://shapely.readthedocs.io/en/stable/manual.html#object.simplify

        """
        polygon = self.boundary(tolerance=tolerance)
        hull_x, hull_y = polygon.exterior.coords.xy
        return hull_x, hull_y

    def plot(self, fscale=10):
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import (LATITUDE_FORMATTER,
                                           LONGITUDE_FORMATTER)

        # First set some plot parameters:
        bbox = self.bbox(buffer=0.1)
        minLon, minLat, maxLon, maxLat = bbox
        extents = [minLon, maxLon, minLat, maxLat]

        # create figure and plot/map
        fig, ax = plt.subplots(
            1,
            1,
            figsize=(fscale, fscale * (maxLon - minLon) / (maxLat - minLat)),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )
        ax.set_extent(extents, crs=ccrs.PlateCarree())

        coastline = cfeature.GSHHSFeature(
            scale="auto", edgecolor="black", facecolor=cfeature.COLORS["land"]
        )
        ax.add_feature(coastline, zorder=0)
        ax.add_feature(cfeature.BORDERS, linewidth=2)

        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=2,
            color="gray",
            alpha=0.5,
            linestyle="--",
        )

        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER

        # Plot the model domain
        bx, by = self.boundary_points()
        poly = plt.Polygon(list(zip(bx, by)), facecolor="r", alpha=0.05)
        ax.add_patch(poly)
        ax.plot(bx, by, lw=2, color="k")
        return fig, ax


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # model = BaseModel()
    x = np.array([0, 1, 2, 3])
    y = np.array([0, 1, 2, 3])
    xx, yy = np.meshgrid(x, y)
    grid = BaseGrid(x=xx, y=yy)
    grid.plot()
    plt.show()
