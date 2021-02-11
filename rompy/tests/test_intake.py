import logging
import pytest

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

def test_catalog():
    import intake
    from intake.catalog import Catalog

    logging.info(intake.cat.rompy_data.discover())

    assert isinstance(intake.cat.rompy_data,Catalog)


def test_intake_local():
    import rompy
    import intake
    import os
    from intake.catalog import Catalog
    from intake.catalog.local import LocalCatalogEntry
    import pandas as pd

    from distributed import LocalCluster, Client
    client=Client(LocalCluster())
    print(client)

    mycat = Catalog.from_dict({
    'test': LocalCatalogEntry('test', 'test fc stack', 'netcdf_fcstack', 
                            args={'urlpath': os.path.dirname(os.path.abspath(__file__)) + '/data/{dt}.000000/',
                            'fn_fmt': 'tab_out.nc',
                            'fmt_fields': {'dt':list(pd.date_range('2021-02-10','2021-02-12').strftime("%Y%m%d"))},
                            'ds_filters': {'subset':['hs']},
                            'hindcast':False}),
    })
    ds = mycat.test.to_dask()
    assert ds.time.shape == (2,121)


def test_intake_remote_stack():
    import rompy
    import pandas as pd
    ds=rompy.cat.bom.wavewatch3_nci(hindcast=False,
                                    fmt_fields={'fcdate':list(pd.date_range('2021-01-21','2021-01-22').strftime("%Y%m%d")),
                                                'hr':['0000'],
                                                'grid':['PER'],
                                                'output':['msh']}).to_dask()

    assert ds.time.shape == (2,169)

def test_intake_remote_hindcast():
    import rompy
    import pandas as pd
    ds=rompy.cat.bom.wavewatch3_nci(hindcast=True,
                                    fmt_fields={'fcdate':list(pd.date_range('2021-01-21','2021-01-22').strftime("%Y%m%d")),
                                                'hr':['0000'],
                                                'grid':['PER'],
                                                'output':['msh']}).to_dask()
    assert ds.time.shape == (193,)


# if __name__ == '__main__':
    # test_intake_remote_stack()
    # test_intake_remote_hindcast()
    # test_intake_local()