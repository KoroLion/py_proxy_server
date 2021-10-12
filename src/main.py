import sys
import sqlite3
from threading import Thread, Lock

from settings import DEFAULT_PROXY_HOST, DEFAULT_PROXY_PORT, DEFAULT_HTTP_HOST, DEFAULT_HTTP_PORT, DATABASE_NAME

from proxy_server import run_proxy_app
from web_server import create_flask_app

from utils.db_utils import create_tables


def main():
    proxy_host, proxy_port = DEFAULT_PROXY_HOST, DEFAULT_PROXY_PORT
    http_host, http_port = DEFAULT_HTTP_HOST, DEFAULT_HTTP_PORT

    if len(sys.argv) > 1:
        proxy_host = sys.argv[1]
    if len(sys.argv) > 2:
        proxy_port = int(sys.argv[2])
    if len(sys.argv) > 3:
        http_host = sys.argv[3]
    if len(sys.argv) > 4:
        http_port = int(sys.argv[4])

    con = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
    create_tables(con)

    mutex = Lock()

    app = create_flask_app()
    app.config['con'] = con
    app.config['mutex'] = mutex
    flask_thread = Thread(target=app.run, kwargs={
        'host': http_host,
        'port': http_port
    })
    flask_thread.start()

    run_proxy_app(proxy_host, proxy_port, con, mutex)


if __name__ == '__main__':
    main()
