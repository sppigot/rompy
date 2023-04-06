from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

import numpy as np
from pydantic import BaseModel, root_validator, validator

from rompy import TEMPLATES_DIR
from rompy.configuration.base import BaseConfig
from rompy.core import BaseGrid
from rompy.data import DataGrid
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
    #    wind_source: SwanDataGrid = SwanDataGrid()
    wind_grid: str = "REG 115.3 -32.8 0.0 2 3 0.3515625 0.234375  NONSTATION 20200221.040000  10800.0 S"
    wind_read: str = "SERIES 'extracted.wind' 1 FORMAT '(3F8.1)'"
    bottom_grid: str = "REG 115.68 -32.76 77 390 150 0.001 0.001 EXC -99.0"
    bottom_file: str = "bathy.bot"
    friction: str = "MAD"
    friction_coeff: str = "0.1"
    spectra_file: str = "boundary.spec"
    subnests: List[SwanConfig] = []

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

    def _get_grid(self, key=None):
        from intake.source.utils import reverse_format

        grid_spec = self.bottom_grid
        fmt = "{gridtype} {x0:f} {y0:f} {rot:f} {nx:d} {ny:d} {dx:f} {dy:f}"
        if "EXC" in grid_spec:  # append excluded value string
            fmt += " EXC {exc:f}"
        grid_params = reverse_format(fmt, grid_spec)
        return SwanGrid(**grid_params)


class SwanGrid(BaseGrid):
    gridtype: Optional[str] = "REG"
    x0: Optional[float]
    y0: Optional[float]
    rot: Optional[float] = 0.0
    dx: Optional[float]
    dy: Optional[float]
    nx: Optional[int]
    ny: Optional[int]
    exc: Optional[float]
    gridfile: Optional[str]
    _x0: Optional[float]
    _y0: Optional[float]
    _rot: Optional[float]
    _dx: Optional[float]
    _dy: Optional[float]
    _nx: Optional[int]
    _ny: Optional[int]

    @validator("gridtype")
    def validate_gridtype(cls, v):
        if v not in ["REG", "CURV"]:
            raise ValueError("gridtype must be one of REG or CURV")
        return v

    #
    # @root_validator
    # def validate_grid(cls, values):
    #     gridtype = values["gridtype"]
    #     x0 = values["x0"]
    #     y0 = values["y0"]
    #     rot = values["rot"]
    #     dx = values["dx"]
    #     dy = values["dy"]
    #     nx = values["nx"]
    #     ny = values["ny"]
    #     exc = values["exc"]
    #     gridfile = values["gridfile"]
    #
    #     if gridtype == "REG":
    #         if not all([x0, y0, rot, dx, dy, nx, ny]):
    #             raise ValueError(
    #                 "x0, y0, rot, dx, dy, nx, ny must be provided for REG grid"
    #             )
    #     elif gridtype == "CURV":
    #         if not gridfile:
    #             raise ValueError("gridfile must be provided for CURV grid")
    #     else:
    #         raise ValueError("Unknown SwanGrid type = " + str(gridtype))
    #     return values
    #
    def __init__(self, **data):
        super().__init__(**data)
        self._x0 = self.x0
        self._y0 = self.y0
        self._rot = self.rot
        self._dx = self.dx
        self._dy = self.dy
        self._nx = self.nx
        self._ny = self.ny
        self._regen_grid()

    def _regen_grid(self):
        if self.gridtype == "REG":
            _x, _y = self._gen_reg_cgrid()
        elif self.gridtype == "CURV":
            _x, _y = self._gen_curv_cgrid()
        self.x = _x
        self.y = _y

    def _gen_reg_cgrid(self):
        # Grid at origin
        i = np.arange(0.0, self.dx * self.nx, self.dx)
        j = np.arange(0.0, self.dy * self.ny, self.dy)
        ii, jj = np.meshgrid(i, j)

        # Rotation
        alpha = -self.rot * np.pi / 180.0
        R = np.array([[np.cos(alpha), -np.sin(alpha)], [np.sin(alpha), np.cos(alpha)]])
        gg = np.dot(np.vstack([ii.ravel(), jj.ravel()]).T, R)

        # Translation
        x = gg[:, 0] + self.x0
        y = gg[:, 1] + self.y0

        x = np.reshape(x, ii.shape)
        y = np.reshape(y, ii.shape)
        return x, y

    def _gen_curv_cgrid(self):
        """loads a SWAN curvilinear grid and returns cgrid lat/lons and
        command to be used in SWAN contol file. The Default grid is one I made using
        Deltares' RGFGrid tool and converted to a SWAN-friendly formate using Deltares
        OpenEarth code "swan_io_grd.m"

        """
        # number of grid cells in the 'x' and 'y' directions:
        # (you can get this from d3d_qp.m or other Deltares OpenEarth code)
        nX = self.nx
        nY = self.ny

        grid_Data = open(self.gridpath).readlines()
        ix = grid_Data.index("x-coordinates\n")
        iy = grid_Data.index("y-coordinates\n")
        lons = []
        lats = []
        for idx in np.arange(ix + 1, iy):
            lons.append(re.sub("\n", "", grid_Data[idx]).split())
        for idx in np.arange(iy + 1, len(grid_Data)):
            lats.append(re.sub("\n", "", grid_Data[idx]).split())
        flatten = lambda l: [item for sublist in l for item in sublist]
        lons = np.array(flatten(lons)).astype(np.float)
        lats = np.array(flatten(lats)).astype(np.float)

        x = np.reshape(lats, (nX, nY))
        y = np.reshape(lons, (nX, nY))

        return x, y

    # # The folling properties and setters are necessary
    # # to ensure the grid is regnerated when any one of them changes
    # TODO this needs ot be ported to a framework that works with pydantic
    # @property
    # def x0(self):
    #     return self._x0
    #
    # @x0.setter
    # def x0(self, x0):
    #     self._x0 = x0
    #     self._regen_grid()
    #
    # @property
    # def y0(self):
    #     return self._y0
    #
    # @y0.setter
    # def y0(self, y0):
    #     self._y0 = y0
    #     self._regen_grid()
    #
    # @property
    # def rot(self):
    #     return self._rot
    #
    # @rot.setter
    # def rot(self, rot):
    #     self._rot = rot
    #     self._regen_grid()
    #
    # @property
    # def dx(self):
    #     return self._dx
    #
    # @dx.setter
    # def dx(self, dx):
    #     self._dx = dx
    #     self._regen_grid()
    #
    # @property
    # def dy(self):
    #     return self._dy
    #
    # @dy.setter
    # def dy(self, dy):
    #     self._dy = dy
    #     self._regen_grid()
    #
    # @property
    # def nx(self):
    #     return self._nx
    #
    # @nx.setter
    # def nx(self, nx):
    #     self._nx = nx
    #     self._regen_grid()
    #
    # @property
    # def ny(self):
    #     return self._ny
    #
    # @ny.setter
    # def ny(self, ny):
    #     self._ny = ny
    #     self._regen_grid()
    #
    # @property
    # def exc(self):
    #     return self._exc
    #
    # @exc.setter
    # def exc(self, exc):
    #     self._exc = exc
    #
    @property
    def inpgrid(self):
        if self.gridtype == "REG":
            inpstr = f"REG {self.x0} {self.y0} {self.rot} {self.nx-1:0.0f} {self.ny-1:0.0f} {self.dx} {self.dy}"
            if self.exc is not None:
                inpstr += f" EXC {self.exc}"
            return inpstr
        elif self.gridtype == "CURV":
            raise NotImplementedError("Curvilinear grids not supported yet")
            # return f'CURVilinear {self.nx-1:0.0f} {self.ny-1:0.0f} \nREADGRID COOR 1 \'{os.path.basename(self.gridpath)}\' 1 0 1 FREE'

    @property
    def cgrid(self):
        if self.gridtype == "REG":
            return f"REG {self.x0} {self.y0} {self.rot} {self.dx*self.nx} {self.dy*self.ny} {self.nx-1:0.0f} {self.ny-1:0.0f}"
        elif self.gridtype == "CURV":
            raise NotImplementedError("Curvilinear grids not supported yet")
            # return (f'CURVilinear {self.nx-1:0.0f} {self.ny-1:0.0f}',f'READGRID COOR 1 \'{os.path.basename(self.gridpath)}\' 1 0 1 FREE')

    def nearby_spectra(self, ds_spec, dist_thres=0.05, plot=True):
        """Find points nearby and project to the boundary

        Parameters
        ----------
        ds_spec: xarray.Dataset
            an XArray dataset of wave spectra at a number of points.
            Dataset variable names standardised using wavespectra.read_*
            functions.

            See https://wavespectra.readthedocs.io/en/latest/api.html#input-functions
        dist_thres: float, optional [Default: 0.05]
            Maximum distance to translate the input spectra to the grid boundary
        plot: boolean, optional [Default: True]
            Generate a plot that shows the applied projections

        Returns
        -------
        xarray.Dataset
            A subset of ds_spec with lat and lon coordinates projected to the boundary
        """

        bbox = self.bbox(buffer=dist_thres)
        minLon, minLat, maxLon, maxLat = bbox

        inds = np.where(
            (ds_spec.lon > minLon)
            & (ds_spec.lon < maxLon)
            & (ds_spec.lat > minLat)
            & (ds_spec.lat < maxLat)
        )[0]
        ds_spec = ds_spec.isel(site=inds)

        # Work out the closest spectral points
        def _nearestPointOnLine(p1, p2, p3):
            # calculate the distance of p3 from the line between p1 and p2 and return
            # the closest point on the line

            from math import fabs, sqrt

            a = p2[1] - p1[1]
            b = -1.0 * (p2[0] - p1[0])
            c = p2[0] * p1[1] - p2[1] * p1[0]

            dist = fabs(a * p3[0] + b * p3[1] + c) / sqrt(a**2 + b**2)
            x = (b * (b * p3[0] - a * p3[1]) - a * c) / (a**2 + b**2)
            y = (a * (-b * p3[0] + a * p3[1]) - b * c) / (a**2 + b**2)

            return dist, x, y

        bx, by = self.boundary_points()
        pol = np.stack([bx, by])

        # Spectra points
        ds_spec.lon.load()
        ds_spec.lat.load()
        ds_spec["lon_original"] = ds_spec["lon"]
        ds_spec["lat_original"] = ds_spec["lat"]
        p3s = list(zip(ds_spec.lon.values, ds_spec.lat.values))

        if plot:
            fig, ax = self.plot()
            ax.scatter(ds_spec.lon, ds_spec.lat)

        specPoints = []
        specPointCoords = []
        for i in range(pol.shape[1] - 1):
            p1 = pol[:, i]
            p2 = pol[:, i + 1]
            line = np.stack((p1, p2))
            output = np.array(
                list(map(lambda xi: _nearestPointOnLine(p1, p2, xi), p3s))
            )
            dists = output[:, 0]
            segmentPoints = output[:, 1:]
            inds = np.where((dists < dist_thres))[0]

            # Loop through the points projected onto the line
            for ind in inds:
                specPoint = ds_spec.isel(site=ind)

                segLon = segmentPoints[ind, 0]
                segLat = segmentPoints[ind, 1]

                if plot:
                    ax.plot(
                        [segLon, specPoint.lon],
                        [segLat, specPoint.lat],
                        color="r",
                        lw=2,
                    )
                    ax.scatter(specPoint.lon, specPoint.lat, marker="o", color="b")
                    ax.scatter(segLon, segLat, marker="x", color="g")

                specPoint["lon"] = segLon
                specPoint["lat"] = segLat
                specPoints.append(specPoint)

            logger.debug(f"Segment {i} - Indices {inds}")

        if plot:
            fig.show()

        ds_boundary = xr.concat(specPoints, dim="site")
        return ds_boundary


class SwanDataGrid(DataGrid):
    """This class is used to write SWAN data from a dataset.

    parameters
    ----------

    """

    def stage(self, staging_dir: str, grid: SwanGrid = None):
        inpwind, readwind = self.ds.swan.to_inpgrid(
            dest_path=os.path.join(staging_dir, f"{self.type}.nc"),
            var="WIND",
            grid=grid,
            z1="u10",
            z2="v10",
        )
        return inpwind, readwind
