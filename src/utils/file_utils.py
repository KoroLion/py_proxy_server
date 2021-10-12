def read_file(path: str) -> str:
    f = open(path, 'r')
    data = f.read()
    return data
