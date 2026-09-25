from __future__ import annotations

import hmac
import os
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Se mantiene una clave de 32 bytes para trabajar con AES-256.
KEY_BYTES = 32
# El IV ocupa 16 bytes porque coincide con el tamaño de bloque de AES.
IV_BYTES = 16


# Genera una clave maestra aleatoria utilizando el generador seguro del sistema operativo.
def generate_session_key() -> bytes:
    return os.urandom(KEY_BYTES)


# A partir de la clave maestra derivamos dos claves independientes:
# una para cifrado AES y otra para HMAC.
# De esta forma evitamos reutilizar la misma clave para funciones distintas.
def derive_keys(master_key: bytes) -> tuple[bytes, bytes]:
    okm = HKDF(algorithm=hashes.SHA256(), length=64, salt=None, info=b"ssi-act1-v1").derive(master_key)
    return okm[:32], okm[32:]


# Cifra los datos usando AES-CBC.
# Se genera un IV aleatorio y se aplica PKCS7 para ajustar el tamaño al bloque AES.
def aes_cbc_encrypt(plaintext: bytes, aes_key: bytes) -> tuple[bytes, bytes]:
    iv = os.urandom(IV_BYTES)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).encryptor()
    return iv, enc.update(padded) + enc.finalize()


# Descifra el contenido y elimina el relleno PKCS7.
# Si los datos han sido alterados es posible que el proceso falle.
def aes_cbc_decrypt(iv: bytes, ciphertext: bytes, aes_key: bytes) -> bytes:
    dec = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


# Cifra un archivo completo utilizando AES-CBC.
# El IV se guarda en un fichero independiente para usarlo en el descifrado.
def encrypt_file(src: Path, dst: Path, master_key: bytes) -> None:
    aes_key, _ = derive_keys(master_key)
    iv, ct = aes_cbc_encrypt(src.read_bytes(), aes_key)
    dst.write_bytes(ct)
    dst.with_suffix(dst.suffix + ".iv").write_bytes(iv)


# Recupera el IV almacenado, descifra el contenido y genera el archivo original.
def decrypt_file(src: Path, dst: Path, master_key: bytes) -> None:
    aes_key, _ = derive_keys(master_key)
    iv = src.with_suffix(src.suffix + ".iv").read_bytes()
    dst.write_bytes(aes_cbc_decrypt(iv, src.read_bytes(), aes_key))


# Calcula el HMAC de los datos.
# Se añade la longitud de cada bloque antes de procesarlo para evitar
# ambigüedades entre distintas combinaciones de entradas.
def compute_hmac(mac_key: bytes, *parts: bytes) -> bytes:
    h = hmac.new(mac_key, digestmod=sha256)
    for part in parts:
        h.update(len(part).to_bytes(4, "big"))
        h.update(part)
    return h.digest()


# Comprueba si el HMAC recibido coincide con el calculado localmente.
# compare_digest evita problemas derivados de comparaciones dependientes del tiempo.
def verify_hmac(mac_key: bytes, tag: bytes, *parts: bytes) -> bool:
    return hmac.compare_digest(compute_hmac(mac_key, *parts), tag)


# Genera un par de claves RSA.
# Se utilizan 3072 bits y exponente 65537, una configuración habitual.
def generate_rsa_keypair(bits: int = 3072):
    return rsa.generate_private_key(public_exponent=65537, key_size=bits)


# Guarda las claves RSA en disco.
# La clave privada se almacena con permisos restrictivos.
def save_keypair(private_key, priv_path: Path, pub_path: Path) -> None:
    priv_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    priv_path.chmod(0o600)
    pub_path.write_bytes(public_key_pem(private_key.public_key()))


# Convierte la clave pública al formato PEM.
def public_key_pem(public_key) -> bytes:
    return public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


# Carga una clave privada desde un fichero PEM.
def load_private(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


# Carga una clave pública a partir de su representación PEM.
def load_public_pem(pem: bytes):
    return serialization.load_pem_public_key(pem)


# Calcula la huella SHA-256 de la clave pública.
# Esta huella permite verificar la identidad del servidor.
def fingerprint(public_key) -> str:
    der = public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return sha256(der).hexdigest()


_OAEP = lambda: asym_padding.OAEP(mgf=asym_padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
_PSS = lambda: asym_padding.PSS(mgf=asym_padding.MGF1(hashes.SHA256()), salt_length=asym_padding.PSS.MAX_LENGTH)


# Cifra la clave de sesión utilizando RSA-OAEP.
# Dos cifrados de la misma clave producirán resultados diferentes.
def rsa_encrypt_key(public_key, master_key: bytes) -> bytes:
    return public_key.encrypt(master_key, _OAEP())


# Recupera la clave de sesión utilizando la clave privada RSA.
def rsa_decrypt_key(private_key, wrapped: bytes) -> bytes:
    return private_key.decrypt(wrapped, _OAEP())


# Genera una firma digital RSA-PSS sobre los datos indicados.
def rsa_sign(private_key, data: bytes) -> bytes:
    return private_key.sign(data, _PSS(), hashes.SHA256())


# Comprueba si la firma digital es válida.
# Devuelve True o False en lugar de propagar la excepción.
def rsa_verify(public_key, signature: bytes, data: bytes) -> bool:
    from cryptography.exceptions import InvalidSignature

    try:
        public_key.verify(signature, data, _PSS(), hashes.SHA256())
        return True
    except InvalidSignature:
        return False
