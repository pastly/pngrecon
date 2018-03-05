from ..util.log import log_stderr as log
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from getpass import getpass


def gen_salt():
    return os.urandom(16)


def prompt_password(for_encryption=True, empty_okay=False):
    pw1 = None
    pw2 = None
    prompt = 'Enter a strong passphrase with which to encrypt this data: ' \
        if for_encryption else 'Enter the passphrase used to encrypt this ' \
        'data: '
    while True:
        pw1 = getpass(prompt)
        if for_encryption:
            pw2 = getpass('Again: ')
            if pw1 != pw2:
                log('Passphrases do not match.')
            elif pw1 == '' and not empty_okay:
                log('Passphrase may not be empty')
            else:
                break
        else:
            if pw1 == '' and not empty_okay:
                log('Passphrase may not be empty')
            else:
                break
    return bytes(pw1, 'utf-8')


def gen_key(password=None, salt=None, for_encryption=True):
    ''' If no password given, prompt the user. If no salt, generate a random
    one. if we need to prompt for a password, tell promp_password whether or
    not it is for encryption so it can change its prompt string. '''
    password = prompt_password(for_encryption=for_encryption) \
        if password is None else password
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
    ''' Try decrypting data with the given fernet structure. If all goes well,
    return True and the decrypted data. Else return False and an error
    message '''
    try:
        d = fernet.decrypt(base64.urlsafe_b64encode(data))
    except InvalidToken as e:
        return False, 'Passphrase appears to be incorrect'
    return True, d
