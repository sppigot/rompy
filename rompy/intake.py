#-----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO 
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
#-----------------------------------------------------------------------------

from intake_xarray.base import DataSourceMixin
from pandas import to_timedelta

import logging

logger = logging.getLogger('rompy.intake')

class NetCDFFCStackSource(DataSourceMixin):
    """An extension of intake-xarray in an opinionated fashion to open a stack of forecast model results stored as netcdf using xarray.

    Expands urlpath with the product of values passed in parameter ``fmt_fields`` to establish a finite set of urls to stack. Uses fsspec so that the file system can be on a local or http. Useful for subsetting catalogs of netcdf files. Defers to XArray for file opening and backend driver selection.

    Parameters
    ----------
    urlpath : str
        Templated path to scan for source file(s). May include format
        pattern strings.
        Some examples:
            - ``{{ CATALOG_DIR }}/data/{year}/air_{month}.nc``
            - ``https://some.thredds.server/thredds/catalog/model/{year}/{month}/catalog.html``
    fn_fmt : str, optional
        Templated file name to check for existence in the broadcast urlpath
        Example:
            - ``air_{month}.nc``
    fmt_fields: dict
        Dictionary of keys corresponding to urlpath format entries. The product of 
        all values is broadcast across urlpath to establish a finite set of locations 
        to look for source files.
    url_replace:
        Dictionary of string substitutions to be made on found urls.
        Example:
            - {'catalog':'dodsC'}
    ds_filters:
        Dictionary of common dataset manipulations that are applied in order 
        during dataset preprocessing. Configurable from catalog entry yaml. 
        Filters currently available are ['sort','subset','crop','timenorm','rename']
        Examples:
            - {'rename':{'dir':'mean_dir'},
               'sort':['direction'],
               'timenorm':'1H',
               'crop':{'lon':slice(-32.2,-33.2),
                       'lat':slice(114.,115.)}
               }
        Additional documentation to follow - see source code for xarray 
        implementation details.
    startdt, enddt: datetime, optional
        Start and end dates to crop final stacked dataset to. 
    hindcast: bool, optional
        Rather than return a stack of forecasts, return a dataset with a 
        unique time dimension selecting the minimum lead time for each time point. 
        Useful for establishing a pseudo-reanalysis dataset from a stack of forecasts.
    chunks : int or dict, optional
        Chunks is used to load the new dataset into dask
        arrays. ``chunks={}`` loads the dataset with dask using a single
        chunk for all arrays.
    xarray_kwargs: dict
        Additional xarray kwargs for xr.open_dataset().
    storage_options: dict
        If using a remote fs (whether caching locally or not), these are
        the kwargs to pass to that FS.
    """
    name = 'netcdf_fcstack'

    def __init__(self, urlpath, fn_fmt='', fmt_fields=None, url_replace=None, ds_filters=None,
                 startdt = None, enddt = None, hindcast = False,
                 chunks=None, xarray_kwargs=None, metadata=None,
                 path_as_pattern=True, storage_options=None, **kwargs):
        self.urlpath = urlpath
        self.fn_fmt = fn_fmt
        self.url_replace = url_replace or {}
        self.fmt_fields = fmt_fields or {}
        self.ds_filters = ds_filters or {}
        self.startdt = startdt
        self.enddt = enddt
        self.hindcast = hindcast
        self.chunks = chunks
        self.xarray_kwargs = xarray_kwargs or {}
        self._ds = None

        self._filter_fns = {'sort': self._sort_filter,
                            'subset': self._subset_filter,
                            'crop': self._crop_filter,
                            'timenorm': self._timenorm_filter,
                            'rename':self._rename_filter}

        super(NetCDFFCStackSource, self).__init__(metadata=metadata, **kwargs)

    def _sort_filter(self,ds,coords):
        for c in coords:
            if c in ds:
                ds = ds.sortby(c)
        return ds

    def _subset_filter(self,ds,data_vars):
        if data_vars is not None:
            ds = ds[data_vars]
        return ds

    def _crop_filter(self,ds,bbox):
        if bbox is not None:
            this_crop = {k:bbox[k] for k in bbox.keys() if k in ds.dims.keys()}
            ds = ds.sel(this_crop)
        return ds

    def _timenorm_filter(self,ds,interval='1 h'):
        interval = to_timedelta(interval)
        ds['init_time'] = ds['time'][0]
        ds['lead_time'] = (ds['time']-ds['time'][0])/interval
        ds = ds.set_coords('init_time')
        ds = ds.swap_dims({'time':'lead_time'})
        return ds

    def _rename_filter(self,ds,varmap):
        ds = ds.rename(varmap)
        return ds

    def _walk_http_server(self):
        # from fsspec.implementations.http import HTTPFileSystem
        from fsspec import filesystem
        from fsspec.utils import get_protocol
        from os.path import dirname
        from functools import reduce
        from operator import iconcat
        from dask import delayed, compute
        import dask.config as dc
        from .utils import dict_product

        # Targetted scans of the file system based on date range
        test_urls = set([self.urlpath.format(**pv) for pv in dict_product(self.fmt_fields)])
        test_fns = set([self.fn_fmt.format(**pv) for pv in dict_product(self.fmt_fields)])

        fs = filesystem(get_protocol(self.urlpath))

        def check_url(fs,test_url,test_fns):
            urls = []
            if fs.exists(test_url):
                for url, _ , links in fs.walk(test_url):
                    urls += [dirname(url) + '/' + fn for fn in links if fn in test_fns]
            return urls

        with dc.set(scheduler='threads'):
            valid_urls = compute(*[delayed(check_url)(fs,test_url,test_fns) for test_url in test_urls])
        valid_urls = sorted(reduce(iconcat,valid_urls,[]))

        for f,r in self.url_replace.items():
            valid_urls = [u.replace(f,r) for u in valid_urls]

        return valid_urls 

    def _open_dataset(self):
        import xarray as xr
        from dask import delayed, compute
        import dask.config as dc

        def _open_single_dataset(url,filters):
            ds = xr.open_dataset(url,chunks={}, **self.xarray_kwargs)
            for fn, params in filters.items():
                if isinstance(fn,str):
                    fn = self._filter_fns[fn]
                ds = fn(ds,params)
            return ds

        urls = self._walk_http_server()

        # Ensure a time normalisation filter is applied to each dataset
        if ('timenorm' not in self.ds_filters.keys()) and (self._timenorm_filter not in self.ds_filters.keys()):
            self.ds_filters[self._timenorm_filter]='1h'

        with dc.set(scheduler='threads'):
            dsets = compute([delayed(_open_single_dataset)(url,self.ds_filters) for url in urls])[0]

        if len(urls) == 0:
            raise ValueError(f'No urls matched for query: {self}')
        elif len(urls) > 1:
            ds = xr.concat(dsets, dim='init_time')
        else:
            logger.info(f'Only one URL returned: {urls}')
            ds = dsets[0]
            ds = ds.expand_dims('init_time')

        ds = ds.stack(forecast_time=['init_time','lead_time'])

        if self.hindcast:
            max_init_time = ds['init_time'].groupby('time').max()
            min_lead_time = ds['lead_time'].groupby('time').min()
            ds = ds.sel(forecast_time=list(zip(max_init_time.values, min_lead_time.values)))
            ds = ds.reset_index('forecast_time').rename({'forecast_time':'time'})
        else:
            ds = ds.reset_index('forecast_time')
            ds = ds.swap_dims({'forecast_time':'time'})
            
        # Finally return the composed dataset, cropped back to cover the requested time period
        if self.startdt is not None:
            ds = ds.sel(time=slice(self.startdt,self.enddt))

        self._ds = ds


