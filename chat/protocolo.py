"""
protocolo.py
Contrato común entre el servidor y el cliente del chat.

Define dos cosas que ambos lados deben respetar:
  1. Cómo se separan los mensajes dentro del flujo TCP (delimitador de fin de línea).
  2. Cómo se ve un mensaje en pantalla (formateadores basados en una clase abstracta).

Regla del protocolo: la PRIMERA línea que envía un cliente es su alias;
todas las líneas siguientes son mensajes de chat.
"""

import socket                          # Módulo estándar para comunicación por red (sockets TCP)
from abc import ABC, abstractmethod    # Herramientas para definir clases abstractas (contratos)
from datetime import datetime          # Para obtener la hora actual en el formateador con hora
from typing import Optional            # Optional[str] = "puede ser un texto o None (nada)"


# --- CONSTANTES DEL PROTOCOLO ---
# Se definen en un solo lugar para que servidor y cliente usen exactamente los mismos valores.

CODIFICACION = "utf-8"       # Forma de convertir texto a bytes y viceversa (soporta tildes y ñ)
DELIMITADOR = b"\n"          # Byte que marca el final de cada mensaje (salto de línea)
TAMANO_BUFFER = 1024         # Máximo de bytes que se leen del socket en cada llamada a recv()


# --- ENVÍO DE MENSAJES ---

def enviar_mensaje(conexion: socket.socket, texto: str) -> None:
    """Convierte el texto a bytes, le agrega el delimitador y lo envía completo por el socket."""
    # Se quitan saltos de línea internos para que un mensaje nunca se parta en dos
    texto_limpio = texto.replace("\n", " ")
    # encode() convierte el texto en bytes; se suma el delimitador al final
    datos = texto_limpio.encode(CODIFICACION) + DELIMITADOR
    # sendall() garantiza que se envíen todos los bytes, aunque la red los mande por partes
    conexion.sendall(datos)


# --- RECEPCIÓN DE MENSAJES ---

class LectorMensajes:
    """
    Lee mensajes completos desde un socket.

    TCP entrega un flujo continuo de bytes: un recv() puede traer medio mensaje
    o varios mensajes pegados. Esta clase acumula los bytes en un buffer y solo
    entrega un mensaje cuando encuentra el delimitador.
    """

    def __init__(self, conexion: socket.socket):
        self._conexion = conexion    # Socket del que se van a leer los datos
        self._pendiente = b""        # Bytes recibidos que todavía no forman un mensaje completo

    def leer(self) -> Optional[str]:
        """
        Devuelve el siguiente mensaje completo como texto.
        Devuelve None si la otra parte cerró la conexión.
        """
        # Mientras no haya un delimitador en lo acumulado, seguimos leyendo del socket
        while DELIMITADOR not in self._pendiente:
            # recv() espera (bloquea) hasta que lleguen datos; devuelve bytes
            datos = self._conexion.recv(TAMANO_BUFFER)
            # Si recv() devuelve vacío, la otra parte cerró la conexión de forma ordenada
            if not datos:
                return None
            # Se agregan los bytes nuevos al final de lo acumulado
            self._pendiente += datos

        # partition() corta en el PRIMER delimitador: (antes, delimitador, después)
        linea, _, resto = self._pendiente.partition(DELIMITADOR)
        # Lo que sobra (el inicio del siguiente mensaje) se guarda para la próxima lectura
        self._pendiente = resto
        # Recién ahora se convierte a texto: así nunca se decodifica una letra a medias.
        # errors="replace" evita que un byte inválido tumbe la conexión.
        return linea.decode(CODIFICACION, errors="replace").strip()


# --- FORMATO VISUAL DE LOS MENSAJES (Principio Abierto/Cerrado) ---

class FormateadorMensaje(ABC):
    """
    Contrato (clase abstracta) para dar formato visual a los mensajes del chat.
    El servidor depende de este contrato y no de una implementación concreta,
    así se puede cambiar el formato sin tocar la lógica de red ni de difusión.
    """

    @abstractmethod
    def formatear_mensaje(self, alias: str, texto: str) -> str:
        """Da formato a un mensaje escrito por un usuario."""

    @abstractmethod
    def formatear_aviso(self, texto: str) -> str:
        """Da formato a un aviso del sistema (alguien entró o salió)."""


class FormateadorSimple(FormateadorMensaje):
    """Formato básico pedido en el enunciado: [Juan]: Hola a todos"""

    def formatear_mensaje(self, alias: str, texto: str) -> str:
        # f-string: inserta el valor de las variables dentro de las llaves {}
        return f"[{alias}]: {texto}"

    def formatear_aviso(self, texto: str) -> str:
        # Los avisos se distinguen con asteriscos
        return f"*** {texto} ***"


class FormateadorConHora(FormateadorMensaje):
    """Variante que antepone la hora: [21:30] [Juan]: Hola a todos"""

    def formatear_mensaje(self, alias: str, texto: str) -> str:
        # strftime("%H:%M") convierte la hora actual en texto con formato horas:minutos
        hora = datetime.now().strftime("%H:%M")
        return f"[{hora}] [{alias}]: {texto}"

    def formatear_aviso(self, texto: str) -> str:
        hora = datetime.now().strftime("%H:%M")
        return f"[{hora}] *** {texto} ***"
