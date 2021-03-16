import logging
import pytest
# import rompy

import sys
print(sys.path)

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

def test_catalog():
    import intake
    from intake.catalog import Catalog

    logging.info(intake.cat.rompy_data.discover())

    assert isinstance(intake.cat.rompy_data,Catalog)


def test_intake_local_stack():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_stack.to_dask()

    assert ds.time.shape == (2,121)

def test_intake_local_stack_single():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_stack_single.to_dask()

    assert ds.time.shape == (121,)

def test_intake_local_stack_single_time():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_stack_single_time.to_dask()

    assert ds.time.shape == (109,)

def test_intake_local_hindcast():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_hindcast.to_dask()

    assert ds.time.shape == (145,)

def test_intake_local_hindcast_single():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_hindcast_single.to_dask()

    assert ds.time.shape == (121,)

def test_intake_local_hindcast_single_time():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_hindcast_single_time.to_dask()

    assert ds.time.shape == (109,)

def test_intake_local_hindcast_time():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_hindcast_time.to_dask()

    assert ds.time.shape == (25,)

def test_intake_local_stack_time():
    import rompy
    import intake
    import os

    mycat = intake.open_catalog(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data','catalog.yaml'))
    ds = mycat.local_stack_time.to_dask()

    assert ds.time.shape == (2,49)

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


if __name__ == '__main__':
    # test_intake_remote_stack()
    # test_intake_remote_hindcast()
    # test_intake_local()
    test_intake_local_hindcast_time()
    # test_intake_local_stack_single_time()