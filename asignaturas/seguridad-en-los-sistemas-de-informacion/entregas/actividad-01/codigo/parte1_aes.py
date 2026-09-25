from __future__ import annotations

from pathlib import Path

import crypto_utils as cu

OUT = Path(__file__).parent / "salida"
OUT.mkdir(exist_ok=True)

TEXTO = (
    "INFORME CONFIDENCIAL - Copia de seguridad del cliente 0042.\n"
    "Saldo pendiente: 12.480,55 EUR. IBAN: ES91 2100 0418 4502 0005 1332.\n"
    "Este archivo debe llegar al servidor sin que nadie lo lea ni lo modifique.\n"
)


# Devuelve las posiciones donde dos secuencias de bytes son diferentes.
# Resulta útil para analizar modificaciones tras una alteración.
def diff_bytes(a: bytes, b: bytes) -> list[int]:
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def main() -> None:
    original = OUT / "original.txt"
    cifrado = OUT / "original.enc"
    recuperado = OUT / "recuperado.txt"
    original.write_text(TEXTO, encoding="utf-8")

    # Generación del escenario de cifrado usando AES-256-CBC.
    print("=== Pregunta 1: cifrado AES-256-CBC ===")
    master = cu.generate_session_key()
    aes_key, mac_key = cu.derive_keys(master)
    cu.encrypt_file(original, cifrado, master)
    iv = cifrado.with_suffix(".enc.iv").read_bytes()
    print(f"Longitud de la clave: {len(master) * 8} bits")
    print(f"Archivo original : {original.stat().st_size} bytes")
    print(f"Archivo cifrado  : {cifrado.stat().st_size} bytes (incluye relleno PKCS7)")
    print(f"IV (hex)         : {iv.hex()}")
    print(f"Primeros bytes cifrados (hex): {cifrado.read_bytes()[:24].hex()}...")

    # Se modifica un único bit en distintas posiciones para observar
    # cómo afecta al descifrado en modo CBC.
    print("\n=== Pregunta 2: descifrado y alteración de 1 byte ===")
    cu.decrypt_file(cifrado, recuperado, master)
    print("¿Recuperado idéntico al original?", recuperado.read_bytes() == original.read_bytes())

    ct = cifrado.read_bytes()
    pt = original.read_bytes()
    ultimo = len(ct) // 16 - 1
    casos = [
        ("byte 3 del bloque 0 del texto cifrado", "ct", 3),
        ("byte 5 del bloque 2 del texto cifrado", "ct", 2 * 16 + 5),
        ("byte 5 del último bloque del texto cifrado", "ct", ultimo * 16 + 5),
        ("byte 3 del IV", "iv", 3),
    ]
    for nombre, donde, pos in casos:
        c, v = bytearray(ct), bytearray(iv)
        (c if donde == "ct" else v)[pos] ^= 0x01
        try:
            out = cu.aes_cbc_decrypt(bytes(v), bytes(c), aes_key)
            malos = diff_bytes(out, pt)
            print(f"- Modificado {nombre}: descifra sin error, pero {len(malos)} bytes difieren, posiciones {malos}")
        except ValueError as exc:
            print(f"- Modificado {nombre}: el descifrado FALLA ({exc})")

    # Se calcula un HMAC sobre IV y texto cifrado para garantizar
    # la integridad de la información durante la transmisión.
    print("\n=== Pregunta 3: integridad con HMAC-SHA256 ===")
    tag = cu.compute_hmac(mac_key, iv, ct)
    print(f"HMAC (hex): {tag.hex()}")
    print("Archivo intacto      -> HMAC válido:", cu.verify_hmac(mac_key, tag, iv, ct))
    alterado = bytearray(ct)
    alterado[2 * 16 + 5] ^= 0x01
    print("1 bit alterado en ct -> HMAC válido:", cu.verify_hmac(mac_key, tag, iv, bytes(alterado)))
    iv_alt = bytearray(iv)
    iv_alt[3] ^= 0x01
    print("1 bit alterado en IV -> HMAC válido:", cu.verify_hmac(mac_key, tag, bytes(iv_alt), ct))
    print("=> El servidor descarta el mensaje ANTES de descifrar, sin llegar a usar datos manipulados.")


if __name__ == "__main__":
    main()
