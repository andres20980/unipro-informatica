from __future__ import annotations

from pathlib import Path

import crypto_utils as cu

OUT = Path(__file__).parent / "salida"
OUT.mkdir(exist_ok=True)


def main() -> None:
    original = OUT / "original.txt"
    if not original.exists():
        raise SystemExit("Ejecuta antes parte1_aes.py para crear salida/original.txt")

    # El servidor genera su par de claves RSA.
    # El cliente utilizará la clave pública para proteger la clave de sesión.
    print("=== Pregunta 4: par de claves RSA y cifrado de la clave AES ===")
    server_priv = cu.generate_rsa_keypair(3072)
    cu.save_keypair(server_priv, OUT / "servidor_privada.pem", OUT / "servidor_publica.pem")
    print("Claves guardadas: salida/servidor_privada.pem y salida/servidor_publica.pem")
    print("Tamaño de la clave RSA:", server_priv.key_size, "bits")
    print("Huella SHA-256 de la pública:", cu.fingerprint(server_priv.public_key()))

    # El cliente cifra el archivo con AES, calcula su HMAC y cifra
    # la clave de sesión mediante RSA-OAEP.
    master = cu.generate_session_key()
    aes_key, mac_key = cu.derive_keys(master)
    iv, ct = cu.aes_cbc_encrypt(original.read_bytes(), aes_key)
    tag = cu.compute_hmac(mac_key, iv, ct)
    server_pub = cu.load_public_pem((OUT / "servidor_publica.pem").read_bytes())
    wrapped = cu.rsa_encrypt_key(server_pub, master)
    (OUT / "clave_sesion.enc").write_bytes(wrapped)
    print(f"Clave AES en claro : {len(master)} bytes -> {master.hex()[:32]}...")
    print(f"Clave AES cifrada  : {len(wrapped)} bytes -> {wrapped.hex()[:32]}...")
    print("Dos cifrados de la misma clave son distintos (OAEP es probabilístico):",
          cu.rsa_encrypt_key(server_pub, master) != wrapped)

    # El servidor recupera la clave de sesión, verifica la integridad
    # del mensaje y descifra el contenido recibido.
    print("\n=== Pregunta 5: descifrado en el servidor ===")
    priv = cu.load_private(OUT / "servidor_privada.pem")
    master_srv = cu.rsa_decrypt_key(priv, wrapped)
    aes_srv, mac_srv = cu.derive_keys(master_srv)
    print("Clave recuperada igual a la enviada:", master_srv == master)
    print("HMAC válido:", cu.verify_hmac(mac_srv, tag, iv, ct))
    recibido = cu.aes_cbc_decrypt(iv, ct, aes_srv)
    print("Archivo descifrado idéntico al original:", recibido == original.read_bytes())

    # Simulación de distintos intentos de acceso no autorizado a la información.
    print("\n=== Pregunta 6: interceptación con una clave distinta ===")
    atacante_priv = cu.generate_rsa_keypair(3072)
    print("Se generan claves RSA de un atacante (distintas de las del servidor).")
    try:
        cu.rsa_decrypt_key(atacante_priv, wrapped)
        print("¡PELIGRO! El atacante pudo descifrar la clave.")
    except ValueError as exc:
        print(f"Intento 1: descifrar la clave AES con la privada del atacante -> FALLA ({exc})")
    fake_master = cu.generate_session_key()
    fake_aes, _ = cu.derive_keys(fake_master)
    try:
        cu.aes_cbc_decrypt(iv, ct, fake_aes)
        print("Intento 2: descifrado con una clave AES inventada -> sin error, pero basura (relleno válido por azar)")
    except ValueError:
        print("Intento 2: descifrar el archivo con una clave AES inventada -> FALLA (relleno inválido)")
    print("Intento 3: fuerza bruta sobre la clave AES -> 2^256 posibilidades, inviable.")


if __name__ == "__main__":
    main()
