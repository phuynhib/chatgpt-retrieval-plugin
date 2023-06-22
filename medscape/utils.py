from config import config
from io import StringIO
import sqlalchemy
import pandas as pd

implode = lambda delimiter, array: delimiter.join([str(item) for item in array])

def db_connection(connection_url = None) -> sqlalchemy.engine.base.Engine:
    """
    Returns a sqlalchemy DB connection/engine
    """
    print('config', config)
    if not connection_url:
        connection_url = config['REC_ENGINE2_DB']['URL']
    print('connection_url', connection_url)
    return sqlalchemy.create_engine(connection_url)

   
def read_sql_inmem_uncompressed(query, db_engine) -> pd.core.frame.DataFrame:
    copy_sql = "COPY ({query}) TO STDOUT WITH CSV {head}".format(
       query=query, head="HEADER"
    )
    conn = db_engine.raw_connection()
    cur = conn.cursor()
    store = StringIO()
    cur.copy_expert(copy_sql, store)
    store.seek(0)
    df = pd.read_csv(store)
    return df
