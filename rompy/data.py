# write pydantic model to read xarray data from intake catalogs, filter, and write to netcdf

import shutil
from typing import Optional

import cloudpathlib
import intake
from pydantic import BaseModel, FilePath, FileUrl, root_validator, validator

# from .filters import lonlat_filter, time_filter, variable_filter


class DataPath(BaseModel):
    """Data source for model ingestion. This is intended to be a generic data source
    for files that simply need to be copied to the model directory.

    Can be either a local file or a remote file.

    Parameters
    ----------
    path: str


    """

    path: pathlib.Path

    def stage(self, dest: str) -> "DataSourceFile":
        """Copy the data source to a new location"""
        pathlib.Path(dest).write_bytes(self.path.read_bytes())
        return DataPath(path=dest)


# class DataSourceFileGrid(DataSourceFile):
#     variable: Optional[str] = None
#     start: Optional[str] = None
#     end: Optional[str] = None
#     bbox: Optional[str] = None
#     variables: Optional[list[str]] = None
#
#     def filter(self, ds: xr.Dataset) -> xr.Dataset:
#         """Filter dataset by variable, time, and bounding box"""
#         if self.variable:
#             ds = variable_filter(ds, self.variable)
#         if self.start and self.end:
#             ds = time_filter(ds, self.start, self.end)
#         if self.bbox:
#             ds = bbox_filter(ds, self.bbox)
#         return ds
