#-----------------------------------------------------------------------------
# Copyright (c) 2020 - 2021, CSIRO 
#
# All rights reserved.
#
# The full license is in the LICENSE file, distributed with this software.
#-----------------------------------------------------------------------------

def sort_filter(ds,coords):
    for c in coords:
        if c in ds:
            ds = ds.sortby(c)
    return ds

def subset_filter(ds,data_vars):
    if data_vars is not None:
        ds = ds[data_vars]
    return ds

def crop_filter(ds,bbox):
    if bbox is not None:
        this_crop = {k:bbox[k] for k in bbox.keys() if k in ds.dims.keys()}
        ds = ds.sel(this_crop)
    return ds

def timenorm_filter(ds,interval='hour'):
    from pandas import to_timedelta
    dt = to_timedelta('1 ' + interval)
    ds['init'] = ds['time'][0]
    ds['lead'] = ((ds['time']-ds['time'][0])/dt).astype('int')
    ds['lead'].attrs['units'] = interval
    ds = ds.set_coords('init')
    ds = ds.swap_dims({'time':'lead'})
    return ds

def rename_filter(ds,varmap):
    ds = ds.rename(varmap)
    return ds

def get_filter_fns():
    return {'sort': sort_filter,
            'subset': subset_filter,
            'crop': crop_filter,
            'timenorm': timenorm_filter,
            'rename': rename_filter}

def _open_preprocess(url,chunks,filters,xarray_kwargs):
    import xarray as xr
    ds = xr.open_dataset(url,chunks=chunks,**xarray_kwargs)
    filter_fns = get_filter_fns()
    for fn, params in filters.items():
        if isinstance(fn,str):
            fn = filter_fns[fn]
        ds = fn(ds,params)
    return ds
