import logging
import pytest

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

def test_catalog():
    import intake
    from intake.catalog import Catalog

    logging.info(intake.cat.rompy_data.discover())

    assert isinstance(intake.cat.rompy_data,Catalog)

# def test_intake():
#     import intake
#     from intake.catalog import Catalog
#     from intake.catalog.local import LocalCatalogEntry
#     import pandas as pd

#     mycat = Catalog.from_dict({
#     'eta': LocalCatalogEntry('test', 'test fc stack', 'netcdf_fcstack', 
#                             args={'urlpath': 'https://data-cbr.csiro.au/thredds/catalog/catch_all/oa-roamsurf/ROAMsurf_opendap/swan_perth_fc/{dt}.000000/catalog.html',
#                             'fn_fmt': 'swan_out.nc',
#                             'url_replace': {'catalog':'dodsC'},
#                             'fmt_fields': {'dt':list(pd.date_range('2021-01-19','2021-01-30').strftime("%Y%m%d"))},
#                             'ds_filters': {'subset':['hs']},
#                             'hindcast':True}),
#     })

#     print(mycat.eta.yaml())
#     ds = mycat.eta.to_dask()
#     print(ds)
#     print(ds.sel(time='2021-01-23 00:00'))
