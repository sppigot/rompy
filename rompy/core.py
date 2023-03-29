# -----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
# -----------------------------------------------------------------------------

import datetime
import glob
import json
import logging
import os
import platform
import pprint
import zipfile as zf
from types import SimpleNamespace

import cookiecutter.config as cc_config
import cookiecutter.generate as cc_generate
import cookiecutter.repository as cc_repository
import numpy as np
from pydantic import BaseModel as pyBaseModel
from pydantic_numpy import NDArray

# pydantic interface to BaseNumericalModel
# https://pydantic-docs.helpmanual.io/usage/models/


logger = logging.getLogger(__name__)


class BaseModel(pyBaseModel):
    run_id: str = "run_0001"
    output_dir: str = "simulations"
    settings: dict = {}
    model: str | None = None
    template: str | None = None
    checkout: str | None = None
    # These are temporary until the cookiecutter stuff is sorted out
    _default_context: dict = {}
    _repo_dir: dict = {}

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data):
        super().__init__(**data)

        # The following code is mostly lifted from https://github.com/cookiecutter/cookiecutter/blob/master/cookiecutter/main.py
        # Load cookie-cutter config - see https://cookiecutter.readthedocs.io/en/1.7.0/advanced/user_config.html

        config_dict = cc_config.get_user_config(
            config_file=None,
            default_config=False,
        )

        repo_dir, cleanup = cc_repository.determine_repo_dir(
            template=self.template,
            abbreviations=config_dict["abbreviations"],
            clone_to_dir=config_dict["cookiecutters_dir"],
            checkout=self.checkout,
            no_input=True,
        )

        context_file = os.path.join(repo_dir, "cookiecutter.json")
        logger.debug("context_file is {}".format(context_file))

        context = cc_generate.generate_context(
            context_file=context_file,
            default_context=config_dict["default_context"],
            extra_context=self.settings,
        )

        print("Default context: (from cookiecutter.json)")
        pprint.pprint(context["cookiecutter"])

        self._repo_dir = repo_dir
        self._default_context = context["cookiecutter"]
        #
        if self.settings is None:
            self.settings = {}
        self.settings["_template"] = self.template
        self.settings["_checkout"] = self.checkout
        self.settings["model"] = self.model

        if not os.path.isdir(self.staging_dir):
            os.makedirs(self.staging_dir + "/downloads")

    @property
    def staging_dir(self):
        return os.path.join(self.output_dir, self.run_id)

    @property
    def grid(self):
        return self._get_grid()

    def _get_grid(self):
        """Subclasses should return an instance of core.Grid"""
        raise NotImplementedError

    def save_settings(self):
        with open(self.staging_dir + "/settings.json", "w") as f:
            json.dump(self.settings, f)

    @classmethod
    def load_settings(fn):
        with open(fn) as f:
            defaults = json.load(f)

    def generate(self):
        self.settings["run_id"] = self.run_id
        self.settings["_generated_at"] = str(datetime.datetime.utcnow())
        self.settings["_generated_by"] = os.environ.get("USER")
        self.settings["_generated_on"] = platform.node()

        # regenerate the context so that is is correctly templated
        context = cc_generate.generate_context(
            context_file=os.path.join(self._repo_dir, "cookiecutter.json"),
            extra_context=self.settings,
        )

        staging_dir = cc_generate.generate_files(
            repo_dir=self._repo_dir,
            context=context,
            overwrite_if_exists=True,
            output_dir=self.output_dir,
        )

        # Save the run settings
        self.save_settings()

        return staging_dir

    def zip(self):
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


# write pydantic BaseGrid class


class BaseGrid(pyBaseModel):
    """An object which provides an abstract representation of a grid in some geographic space

    This is the base class for all Grid objects. The minimum representation of a grid are two
    NumPy array's representing the vertices or nodes of some structured or unstructured grid,
    its bounding box and a boundary polygon. No knowledge of the grid connectivity is expected.

    """

    x: NDArray
    y: NDArray

    @property
    def minx(self):
        return np.nanmin(self.x)

    @property
    def maxx(self):
        return np.nanmax(self.x)

    @property
    def miny(self):
        return np.nanmin(self.y)

    @property
    def maxy(self):
        return np.nanmax(self.y)

    def bbox(self, buffer=0.0):
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

    def _get_boundary(self, tolerance=0.2):
        from shapely.geometry import MultiPoint, Polygon

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
        import cartopy.mpl.ticker as cticker
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import (LATITUDE_FORMATTER,
                                           LONGITUDE_FORMATTER)
        from shapely.geometry import MultiPoint, Polygon

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
