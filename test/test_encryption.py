#!/usr/bin/python

# test that privcount's encryption and decryption functions work

# this test will exit successfully if the decrypted data matches the original
# encrypted data

from base64 import b64encode, b64decode
from os import urandom
from random import SystemRandom

import sys

from privcount.util import load_public_key_file, load_private_key_file, encrypt_pk, decrypt_pk, generate_symmetric_key, encrypt_symmetric, decrypt_symmetric, encode_data, decode_data, encrypt, decrypt

import logging
# DEBUG logs every check: use it on failure
# INFO logs each check once
logging.basicConfig(level=logging.INFO)
logging.root.name = ''

# What range of random numbers should we use for ints and longs?
INT_BITS = 64 if sys.maxsize > 2**32 else 32
RAND_INT_BITS = INT_BITS - 1
RAND_LONG_BITS = INT_BITS + 10

# How long should the random string be (in unencoded bytes)?
RAND_STR_BYTES = 20

# The paths to the RSA keys, when in the privcount/test directory
PUBLIC_KEY_PATH = 'keys/sk.cert'
PRIVATE_KEY_PATH = 'keys/sk.pem'

# This is the maximum number of bytes OpenSSL will encrypt with PrivCount's
# current public key size (determined by trying different values)
PK_ENCRYPTION_LENGTH_MAX = 446

# It's unlikely we'll ever send more than a megabyte
SYM_ENCRYPTION_LENGTH_MAX = 1024*1024

def check_pk_encdec(pub_key, priv_key, plaintext):
    """
    Check that plaintext survives pk encryption and descryption intact
    """
    logging.debug("Plaintext is {} bytes".format(len(plaintext)))
    logging.debug("Encrypting with an asymmetric public key:")
    ciphertext = encrypt_pk(pub_key, plaintext)
    logging.debug("Ciphertext is {} bytes base64-encoded, {} bytes raw".format(
        len(ciphertext), len(b64decode(ciphertext))))
    logging.debug("Decrypting ciphertext with an asymmetric private key:")
    resulttext = decrypt_pk(priv_key, ciphertext)
    assert type(plaintext) == type(resulttext)
    assert plaintext == resulttext
    logging.debug("Decrypted data was identical to the original data!")

def check_symmetric_encdec(secret_key, plaintext):
    """
    Check that plaintext survives symmetric encryption and descryption intact
    """
    logging.debug("Plaintext is {} bytes".format(len(plaintext)))
    logging.debug("Encrypting with a symmetric secret key:")
    ciphertext = encrypt_symmetric(secret_key, plaintext)
    # we can't use b64decode on fernet tokens, they use URL-safe base64
    logging.debug("Ciphertext is {} bytes base64-encoded, ~{} bytes raw"
                  .format(len(ciphertext), len(ciphertext)*6/8))
    logging.debug("Decrypting ciphertext with a symmetric secret key:")
    resulttext = decrypt_symmetric(secret_key, ciphertext)
    assert type(plaintext) == type(resulttext)
    assert plaintext == resulttext
    logging.debug("Decrypted data was identical to the original data!")

def check_data_encdec(data_structure):
    """
    Check that data_structure survives encoding and decoding intact
    """
    logging.debug("Encoding data structure into a string:")
    encoded_string = encode_data(data_structure)
    logging.debug("Encoded string is {} bytes base64-encoded, {} bytes raw"
                  .format(len(encoded_string), len(b64decode(encoded_string))))
    logging.debug("Decoding data structure from a string:")
    result = decode_data(encoded_string)
    assert type(result) == type(data_structure)
    assert result == data_structure
    logging.debug("Decoded data was identical to the original data!")

def check_encdec(pub_key, priv_key, data_structure):
    """
    Check that data_structure survives encryption and descryption intact
    """
    logging.debug("Encrypting data structure:")
    ciphertext = encrypt(pub_key, data_structure)
    logging.debug("Decrypting data structure:")
    result_structure = decrypt(priv_key, ciphertext)
    # We could do a recursive data type comparison, but value equality is
    # almost always enough for our purposes
    assert type(data_structure) == type(result_structure)
    assert data_structure == result_structure
    logging.debug("Decrypted data was identical to the original data!")

def check(pub_key, priv_key, data_structure):
    """
    Check that data_structure survives encoding and decoding, and encryption
    and decryption, and retains the same type and value.
    """
    check_data_encdec(data_structure)
    check_encdec(pub_key, priv_key, data_structure)

logging.info("Loading public key {}:".format(PUBLIC_KEY_PATH))
pub_key = load_public_key_file(PUBLIC_KEY_PATH)

logging.info("Loading private key {}:".format(PRIVATE_KEY_PATH))
priv_key = load_private_key_file(PRIVATE_KEY_PATH)

logging.info("Generating {} bytes of plaintext:"
             .format(PK_ENCRYPTION_LENGTH_MAX))
plaintext = b64encode(urandom(PK_ENCRYPTION_LENGTH_MAX*8/6+1))
plaintext = plaintext[:PK_ENCRYPTION_LENGTH_MAX]

check_pk_encdec(pub_key, priv_key, "")
check_pk_encdec(pub_key, priv_key, plaintext[:100])
check_pk_encdec(pub_key, priv_key, plaintext[:200])
check_pk_encdec(pub_key, priv_key, plaintext[:300])
check_pk_encdec(pub_key, priv_key, plaintext)

logging.info("Generating secret key for symmetric encryption:")
secret_key = generate_symmetric_key()

logging.info("Generating {} bytes of plaintext:".format(SYM_ENCRYPTION_LENGTH_MAX))
plaintext = b64encode(urandom(SYM_ENCRYPTION_LENGTH_MAX*8/6+1))
plaintext = plaintext[:SYM_ENCRYPTION_LENGTH_MAX]

check_symmetric_encdec(secret_key, "")
check_symmetric_encdec(secret_key, plaintext[:100])
check_symmetric_encdec(secret_key, plaintext[:PK_ENCRYPTION_LENGTH_MAX])
check_symmetric_encdec(secret_key, plaintext[:1024])
check_symmetric_encdec(secret_key, plaintext[:(10*1024)])
check_symmetric_encdec(secret_key, plaintext[:(100*1024)])
check_symmetric_encdec(secret_key, plaintext)

logging.info("Checking data structure encoding and encryption:")
rand_int_int = int(SystemRandom().getrandbits(RAND_INT_BITS))
rand_int_long = SystemRandom().getrandbits(RAND_INT_BITS)
assert isinstance(rand_int_long, long)
rand_long_long = SystemRandom().getrandbits(RAND_LONG_BITS)
assert isinstance(rand_long_long, long)
rand_double = SystemRandom().random()
rand_string = b64encode(urandom(RAND_STR_BYTES))

logging.info("Checking basic types:")
check(pub_key, priv_key, rand_int_int)
check(pub_key, priv_key, rand_int_long)
check(pub_key, priv_key, rand_long_long)
check(pub_key, priv_key, rand_double)
check(pub_key, priv_key, rand_string)

logging.info("Checking basic containers:")
# currently, we only support lists and dicts
rand_dict = {'rii': rand_int_int, 'ril': rand_int_long, 'rll': rand_long_long,
             'rd': rand_double, 'rs': rand_string}
rand_list = [rand_int_int, rand_int_long, rand_long_long, rand_double,
             rand_string]
check(pub_key, priv_key, rand_dict)
check(pub_key, priv_key, rand_list)

logging.info("Checking nested containers:")
nested_container = [rand_dict, rand_list]

check(pub_key, priv_key, nested_container)

logging.info("Checking containers with multiple references to sub-containers:")
multi_ref_scalar = [rand_int_int, rand_int_int]
multi_ref_object = [rand_long_long, rand_long_long, rand_string, rand_string]
multi_ref_container = [rand_dict, rand_dict, rand_dict]

check(pub_key, priv_key, multi_ref_scalar)
check(pub_key, priv_key, multi_ref_object)
check(pub_key, priv_key, multi_ref_container)

logging.info("Checking large data structures:")

check(pub_key, priv_key, plaintext)
