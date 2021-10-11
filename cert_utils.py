import os
import subprocess
from random import randrange

RND_FILE = 'temp.rnd'


def exec(command, env):
    subprocess.call(command, env=env)


def generate_root_cert(name: str, ca_crt: str, ca_key: str, cert_key: str):
    env = os.environ.copy()
    env['RANDFILE'] = RND_FILE

    exec('openssl genrsa -out {} 2048'.format(ca_key), env)
    exec('openssl req -new -x509 -days 3650 -key {} -out {} -subj "/CN={}"'.format(ca_key, ca_crt, name), env)
    exec('openssl genrsa -out {} 2048'.format(cert_key), env)

    os.unlink(RND_FILE)


def generate_cert(host: str, ca_crt: str, ca_key: str, cert_key: str) -> bytes:
    cert_request_command = 'openssl req -new -key {} -subj "/CN={}" -sha256'.format(cert_key, host)
    cert_req = subprocess.check_output(cert_request_command)

    env = os.environ.copy()
    env['RANDFILE'] = RND_FILE
    serial = randrange(1, 9999999999)
    proc = subprocess.Popen(
        'openssl x509 -req -days 3650 -CA {} -CAkey {} -set_serial "{}"'.format(ca_crt, ca_key, serial),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    cert = proc.communicate(cert_req)[0]
    os.unlink(RND_FILE)
    return cert
