from __future__ import annotations

import os
import time
from pathlib import Path

import crypto_utils as cu

OUT = Path(__file__).parent / "salida"
OUT.mkdir(exist_ok=True)
WINDOW_SECONDS = 60


# Simula el medio de comunicación entre cliente y servidor.
# Además registra los mensajes intercambiados para poder analizarlos.
class Canal:

    def __init__(self) -> None:
        self.log: list[tuple[str, str, dict]] = []

    def send(self, origen: str, destino: str, etapa: str, contenido: dict) -> dict:
        resumen = {k: (v.hex()[:24] + "…" if isinstance(v, bytes) and len(v) > 12 else v) for k, v in contenido.items()}
        print(f"  {origen} -> {destino} | {etapa:<12} | {resumen}")
        self.log.append((origen, etapa, contenido))
        return contenido


# Representa el servidor encargado de recibir y validar mensajes.
class Servidor:
    # Inicializa las claves del servidor y las estructuras necesarias
    # para gestionar sesiones y detectar repeticiones.
    def __init__(self) -> None:
        self._priv = cu.generate_rsa_keypair(3072)
        self.pub = self._priv.public_key()
        self.sesiones: dict[bytes, tuple[bytes, bytes]] = {}
        self.vistos: set[tuple[bytes, bytes]] = set()
        self.recibidos: list[bytes] = []

    # Envía su clave pública y firma el nonce recibido para demostrar
    # que es el propietario legítimo de la clave privada asociada.
    def server_hello(self, client_nonce: bytes) -> dict:
        pem = cu.public_key_pem(self.pub)
        firma = cu.rsa_sign(self._priv, client_nonce + pem)
        return {"clave_publica": pem, "firma": firma}

    # Descifra la clave de sesión enviada por el cliente y almacena
    # las claves derivadas para futuras comunicaciones.
    def key_exchange(self, id_sesion: bytes, wrapped: bytes) -> None:
        master = cu.rsa_decrypt_key(self._priv, wrapped)
        self.sesiones[id_sesion] = cu.derive_keys(master)

    # Flujo de validación del servidor:
    # 1. Comprobar que la sesión existe.
    # 2. Verificar el HMAC.
    # 3. Validar la marca temporal.
    # 4. Detectar posibles repeticiones.
    # 5. Descifrar el contenido.
    def recibir(self, msg: dict, ahora: float | None = None) -> str:
        ahora = time.time() if ahora is None else ahora
        keys = self.sesiones.get(msg["id_sesion"])
        if keys is None:
            return "RECHAZADO: sesión desconocida"
        aes_key, mac_key = keys
        datos = (msg["id_sesion"], msg["id_mensaje"], msg["marca_tiempo"].to_bytes(8, "big"), msg["iv"], msg["cifrado"])
        if not cu.verify_hmac(mac_key, msg["hmac"], *datos):
            return "RECHAZADO: HMAC inválido (mensaje alterado o clave incorrecta)"
        if abs(ahora - msg["marca_tiempo"]) > WINDOW_SECONDS:
            return f"RECHAZADO: marca de tiempo fuera de la ventana de {WINDOW_SECONDS} s (mensaje antiguo)"
        clave = (msg["id_sesion"], msg["id_mensaje"])
        if clave in self.vistos:
            return "RECHAZADO: REPETICIÓN detectada (id_mensaje ya procesado)"
        self.vistos.add(clave)
        contenido = cu.aes_cbc_decrypt(msg["iv"], msg["cifrado"], aes_key)
        self.recibidos.append(contenido)
        return f"ACEPTADO: {len(contenido)} bytes descifrados"


# Representa al cliente que inicia la comunicación con el servidor.
class Cliente:
    # Inicializa el cliente con la huella esperada del servidor.
    # Solo se aceptarán servidores cuya clave coincida con ella.
    def __init__(self, huella_servidor_fijada: str) -> None:
        self.huella_fijada = huella_servidor_fijada
        self.id_sesion = os.urandom(16)
        self.aes_key = self.mac_key = b""

    # Realiza el proceso de conexión:
    # - Verifica la huella de la clave pública.
    # - Comprueba la firma del servidor.
    # - Genera la clave de sesión.
    # - Prepara el intercambio de claves.
    def conectar(self, canal: Canal, server_hello_fn) -> bool:
        nonce = os.urandom(16)
        canal.send("CLIENTE", "SERVIDOR", "ClientHello", {"nonce_cliente": nonce})
        sh = server_hello_fn(nonce)
        canal.send("SERVIDOR", "CLIENTE", "ServerHello", sh)
        pub = cu.load_public_pem(sh["clave_publica"])
        if cu.fingerprint(pub) != self.huella_fijada:
            print("  [CLIENTE] ¡Huella de la clave distinta a la fijada! Posible suplantación. Conexión abortada.")
            return False
        if not cu.rsa_verify(pub, sh["firma"], nonce + sh["clave_publica"]):
            print("  [CLIENTE] Firma del servidor inválida. Conexión abortada.")
            return False
        print("  [CLIENTE] Huella y firma correctas: el servidor es auténtico.")
        master = cu.generate_session_key()
        self.aes_key, self.mac_key = cu.derive_keys(master)
        self.wrapped = cu.rsa_encrypt_key(pub, master)
        return True

    # Envía al servidor la clave de sesión cifrada junto al identificador
    # de la nueva sesión.
    def key_exchange(self, canal: Canal) -> dict:
        return canal.send("CLIENTE", "SERVIDOR", "KeyExchange", {"id_sesion": self.id_sesion, "clave_cifrada": self.wrapped})

    # Construye un mensaje cifrado con identificador único y marca temporal.
    # El HMAC protege todos los campos relevantes del mensaje.
    def mensaje(self, contenido: bytes, marca_tiempo: int | None = None) -> dict:
        iv, ct = cu.aes_cbc_encrypt(contenido, self.aes_key)
        mid = os.urandom(16)
        ts = int(time.time()) if marca_tiempo is None else marca_tiempo
        tag = cu.compute_hmac(self.mac_key, self.id_sesion, mid, ts.to_bytes(8, "big"), iv, ct)
        return {"id_sesion": self.id_sesion, "id_mensaje": mid, "marca_tiempo": ts, "iv": iv, "cifrado": ct, "hmac": tag}


def titulo(t: str) -> None:
    print(f"\n=== {t} ===")


def main() -> None:
    original = OUT / "original.txt"
    if not original.exists():
        raise SystemExit("Ejecuta antes parte1_aes.py")
    datos = original.read_bytes()

    servidor = Servidor()
    canal = Canal()
    huella = cu.fingerprint(servidor.pub)

    # Ejecución completa del protocolo:
    # handshake, intercambio de claves y envío del archivo.
    titulo("Pregunta 7: protocolo completo (handshake + envío del archivo)")
    cliente = Cliente(huella)
    assert cliente.conectar(canal, servidor.server_hello)
    servidor.key_exchange(cliente.id_sesion, cliente.key_exchange(canal)["clave_cifrada"])
    msg = cliente.mensaje(datos)
    canal.send("CLIENTE", "SERVIDOR", "Datos", msg)
    print("  [SERVIDOR] Veredicto:", servidor.recibir(msg))
    print("  Archivo recibido idéntico al original:", servidor.recibidos[-1] == datos)

    # Pruebas frente a mensajes repetidos, mensajes antiguos
    # y modificaciones del contenido durante la transmisión.
    titulo("Pregunta 8: repetición de un mensaje (replay)")
    print("  Un atacante captura el mensaje anterior y lo reenvía SIN cambiar nada:")
    print("  [SERVIDOR] Veredicto:", servidor.recibir(msg))
    print("  Otro mensaje legítimo con contenido nuevo (id_mensaje distinto):")
    print("  [SERVIDOR] Veredicto:", servidor.recibir(cliente.mensaje(b"segundo mensaje legitimo")))
    print("  Mensaje antiguo (marca de tiempo de hace 10 minutos), aunque tenga HMAC válido:")
    print("  [SERVIDOR] Veredicto:", servidor.recibir(cliente.mensaje(b"mensaje viejo", int(time.time()) - 600)))
    print("  Mensaje alterado en 1 bit del texto cifrado:")
    alt = dict(cliente.mensaje(b"otro mensaje"))
    c = bytearray(alt["cifrado"]); c[0] ^= 1; alt["cifrado"] = bytes(c)
    print("  [SERVIDOR] Veredicto:", servidor.recibir(alt))

    # Simulación de un servidor falso.
    # El cliente detecta que la huella no coincide y cancela la conexión.
    titulo("Suplantación del servidor (ataque de intermediario)")
    impostor = Servidor()
    victima = Cliente(huella)
    print("  El cliente conecta con un servidor falso que usa otro par de claves:")
    print("  Conexión establecida:", victima.conectar(Canal(), impostor.server_hello))


if __name__ == "__main__":
    main()
