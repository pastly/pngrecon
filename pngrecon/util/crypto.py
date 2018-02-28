from ..util.log import fail_hard
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


def gen_salt():
    return os.urandom(16)


def prompt_password():
    fail_hard('prompt_password not implemented')


def gen_key(password=None, salt=None):
    password = prompt_password() if password is None else password
    salt = gen_salt() if salt is None else salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    # Fernet wants it in base 64
    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    return salt, f


def encrypt(fernet, data):
    return base64.urlsafe_b64decode(fernet.encrypt(data))


def decrypt(fernet, data):
    return fernet.decrypt(base64.urlsafe_b64encode(data))
