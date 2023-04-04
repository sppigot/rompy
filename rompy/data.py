# write pydantic model to read xarray data from intake catalogs, filter, and write to netcdf

import pathlib
from typing import Optional

import cloudpathlib
import intake
import xarray as xr
from pydantic import BaseModel, FilePath, FileUrl, root_validator, validator

from .filters import Filter

# from .filters import lonlat_filter, time_filter, variable_filter


class DataBlob(BaseModel):
    """Data source for model ingestion. This is intended to be a generic data source
    for files that simply need to be copied to the model directory.

    Must be a local file or a remote file.

    Parameters
    ----------
    path: str
    url: str


    """

    path: Optional[pathlib.Path]
    url: Optional[cloudpathlib.CloudPath]

    @root_validator
    def check_path_or_url(cls, values):
        if values.get("path") is None and values.get("url") is None:
            raise ValueError("Must provide either a path or a url")
        if values.get("path") is not None and values.get("url") is not None:
            raise ValueError("Must provide either a path or a url, not both")
        return values

    def stage(self, dest: str) -> "DataBlob":
        """Copy the data source to a new location"""
        if self.path:
            pathlib.Path(dest).write_bytes(self.path.read_bytes())
        elif self.url:
            pathlib.Path(dest).write_bytes(self.url.read_bytes())
        return DataBlob(path=dest)


class DataGrid(BaseModel):
    """Data source for model ingestion. This is intended to be a generic data source
    for xarray datasets that need to be filtered and written to netcdf.

    Must be a local file (path) or a remote file (url) or intake and dataset id combination.

    Parameters
    ----------
    path: str
    url: str
    catalog: str
    dataset: str
    filter: Filter
    xarray_kwargs: dict
    netcdf_kwargs: dict

    """

    path: Optional[pathlib.Path]
    url: Optional[cloudpathlib.CloudPath]
    catalog: Optional[str]  # TODO make this smarter
    dataset: Optional[str]
    filter: Optional[Filter] = None
    xarray_kwargs: Optional[dict] = {}
    netcdf_kwargs: Optional[dict] = dict(mode="w", format="NETCDF4")
    _ds: Optional[xr.Dataset] = None

    class Config:
        underscore_attrs_are_private = True

    @root_validator
    def check_path_or_url_or_intake(cls, values):
        if values.get("path") is None and values.get("url") is None:
            if values.get("catalog") is None or values.get("dataset") is None:
                raise ValueError(
                    "Must provide either a path or a url or a catalog and dataset"
                )
        if (
            values.get("path") is not None
            and values.get("url") is not None
            and values.get("catalog") is not None
        ):
            raise ValueError("Must provide only one of a path url or catalog")
        return values

    @property
    def ds(self):
        """Return the xarray dataset for this data source."""
        if self._ds is not None:
            return self._ds
        if self.path:
            ds = xr.open_dataset(self.path, **self.xarray_kwargs)
        elif self.url:
            ds = xr.open_dataset(self.url, **self.xarray_kwargs)
        elif self.catalog:
            cat = intake.open_catalog(self.catalog)
            ds = cat[self.dataset].to_dask()
        if self.filter:
            self._ds = self.filter(ds)
        else:
            self._ds = ds
        return self._ds

    def stage(self, dest: str) -> "DataGrid":
        """Write the data source to a new location"""
        self.ds.to_netcdf(dest, mode=self.mode, format=self.format)
        return DataGrid(path=dest, **self.netcdf_kwargs)
