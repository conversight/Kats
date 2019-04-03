"""
This script generates the thrift structures used for unit testing pymapd.
It requires an OmniSci server to be running on localhost:6274 with the default
username, password, and database name.

.. code-block:: console

    python scripts/generate_thrift_structs.py

We run through a series of sql statements using the bindings generated by
thrift. The return values are serialized to python files, which are then
read in and executed by the test suite.
"""
import os
import pickle
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket
from thrift.transport import TTransport
from mapd import MapD
from mapd.ttypes import TMapDException

HERE = os.path.dirname(__file__)
DEST = os.path.join(os.path.dirname(HERE), "tests", "data")


def get_client(host_or_uri, port):
    socket = TSocket.TSocket(host_or_uri, port)
    transport = TTransport.TBufferedTransport(socket)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    client = MapD.Client(protocol)
    transport.open()
    return client


def write(obj, name):
    with open(os.path.join(DEST, name), 'wb') as f:
        pickle.dump(obj, f, protocol=2)


def main():

    db_name = 'mapd'
    user_name = 'mapd'
    passwd = 'HyperInteractive'
    hostname = 'localhost'
    portno = 6274

    client = get_client(hostname, portno)
    session = client.connect(user_name, passwd, db_name)

    drop = 'drop table if exists stocks;'
    client.sql_execute(session, drop, True, None, -1, -1)
    create = ('create table stocks (date_ text, trans text, symbol text, '
              'qty int, price float, vol float, real_date TIMESTAMP);')
    client.sql_execute(session, create, True, None, -1, -1)

    i1 = "INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14,1.1,'2010-01-01 12:01:01');"  # noqa
    i2 = "INSERT INTO stocks VALUES ('2006-01-05','BUY','GOOG',100,12.14,1.2,'2010-01-01 12:02:02');"  # noqa
    client.sql_execute(session, i1, True, None, -1, -1)
    client.sql_execute(session, i2, True, None, -1, -1)
    select = "select * from stocks;"
    colwise = client.sql_execute(session, select, True, None, -1, -1)
    rowwise = client.sql_execute(session, select, False, None, -1, -1)

    write(rowwise, "rowwise.pkl")
    write(colwise, "colwise.pkl")
    # Invalid SQL
    try:
        client.sql_execute(session, "select it;", True, None, -1, -1)
    except TMapDException as e:
        write(e, "invalid_sql.pkl")

    # Valid SQL, non-existant table
    try:
        client.sql_execute(session, "select fake from not_a_table;", True,
                           None, -1, -1)
    except TMapDException as e:
        write(e, "nonexistant_table.pkl")

    # valid table, non-existant column
    try:
        client.sql_execute(session, "select fake from stocks;", True,
                           None, -1, -1)
    except TMapDException as e:
        write(e, "nonexistant_column.pkl")

    client.disconnect(session)


if __name__ == '__main__':
    main()
