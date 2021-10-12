from time import time


def save_to_db(con, mutex, protocol, method, url, request: str, response: str):
    t = round(time())
    stmt = "INSERT INTO requests (time, protocol, method, url, request, response) VALUES (?, ?, ?, ?, ?, ?)"
    values = (t, protocol, method, url, request, response)

    mutex.acquire()

    con.cursor().execute(stmt, values)
    con.commit()

    mutex.release()


def create_tables(con):
    con.cursor().execute('CREATE TABLE IF NOT EXISTS requests (id INTEGER PRIMARY KEY, time INTEGER, protocol TEXT, method TEXT, url TEXT, request TEXT, response TEXT)')
    con.commit()
