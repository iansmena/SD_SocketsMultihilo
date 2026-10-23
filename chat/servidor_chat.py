import socket                          
import threading                       
import logging                         
from abc import ABC, abstractmethod    

from protocolo import (
    LectorMensajes,       
    enviar_mensaje,       
    FormateadorMensaje,   
    FormateadorSimple,    
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- CONTRATO DE DIFUSIÓN (Inversión de Dependencias) ---

class InterfazDifusion(ABC):
    @abstractmethod
    def agregar_cliente(self, conexion: socket.socket) -> None:
        """Registra una conexión nueva en la sala."""

    @abstractmethod
    def eliminar_cliente(self, conexion: socket.socket) -> None:
        """Quita una conexión de la sala."""

    @abstractmethod
    def difundir(self, mensaje: str, remitente: socket.socket) -> None:
        """Envía el mensaje a todos los clientes excepto al remitente."""

class SalaChat(InterfazDifusion):
    """
    Mantiene el registro dinámico de clientes conectados y difunde los mensajes.
    """

    def __init__(self):
        self._clientes = []                 
        self._candado = threading.Lock()    

    def agregar_cliente(self, conexion: socket.socket) -> None:
        with self._candado:
            self._clientes.append(conexion)     

    def eliminar_cliente(self, conexion: socket.socket) -> None:
        with self._candado:
            if conexion in self._clientes:
                self._clientes.remove(conexion)

    def difundir(self, mensaje: str, remitente: socket.socket) -> None:
        pass

class ManejadorCliente:
    def __init__(self, conexion: socket.socket, direccion: tuple,
                 sala: InterfazDifusion, formateador: FormateadorMensaje):
        self._conexion = conexion           
        self._direccion = direccion         
        self._sala = sala                   
        self._formateador = formateador     
        self._alias = None                  

    def _ip_puerto(self) -> str:
        return f"{self._direccion[0]}:{self._direccion[1]}"

    def atender(self) -> None:
        logging.info(f"Cliente conectado desde {self._ip_puerto()}")
        lector = LectorMensajes(self._conexion)
        registrado = False    
        try:
            alias = lector.leer()
            if alias is None:
                return    
            self._alias = alias or "Anonimo"

            self._sala.agregar_cliente(self._conexion)
            registrado = True
            logging.info(f"{self._ip_puerto()} se identificó como '{self._alias}'")
            aviso = self._formateador.formatear_aviso(f"{self._alias} se unió al chat")
            self._sala.difundir(aviso, self._conexion)

            while True:
                texto = lector.leer()
                if texto is None:
                    break     
                if not texto:
                    continue  
                mensaje = self._formateador.formatear_mensaje(self._alias, texto)
                self._sala.difundir(mensaje, self._conexion)

        except (ConnectionResetError, ConnectionAbortedError):
            logging.warning(f"Desconexión abrupta de {self._ip_puerto()}")
        except OSError as error:
            logging.error(f"Error de red con {self._ip_puerto()}: {error}")
        finally:
            if registrado:
                self._sala.eliminar_cliente(self._conexion)
                aviso = self._formateador.formatear_aviso(f"{self._alias} salió del chat")
                self._sala.difundir(aviso, self._conexion)
            self._conexion.close()
            logging.info(f"Cliente desconectado: {self._ip_puerto()}")

class ServidorChat:
    def __init__(self, host: str, puerto: int,
                 sala: InterfazDifusion, formateador: FormateadorMensaje):
        self._host = host
        self._puerto = puerto
        self._sala = sala
        self._formateador = formateador
        self._socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def iniciar(self) -> None:
        try:
            self._socket_servidor.bind((self._host, self._puerto))   
        except OSError:
            logging.error(f"El puerto {self._puerto} ya está en uso. ¿Hay otro servidor abierto?")
            self._socket_servidor.close()
            return
        self._socket_servidor.listen()                           
        self._socket_servidor.settimeout(1.0)
        logging.info(f"Servidor de chat escuchando en {self._host}:{self._puerto}")
        logging.info("Presiona Ctrl+C para detener el servidor")

        try:
            while True:
                try:
                    conexion, direccion = self._socket_servidor.accept()
                except socket.timeout:
                    continue    
                conexion.settimeout(None)
                manejador = ManejadorCliente(conexion, direccion, self._sala, self._formateador)
                hilo = threading.Thread(target=manejador.atender, daemon=True)
                hilo.start()    
        except KeyboardInterrupt:
            logging.info("Servidor detenido por el usuario")
        finally:
            self._socket_servidor.close()

if __name__ == "__main__":
    HOST = "0.0.0.0"    
    PUERTO = 8080       

    sala = SalaChat()
    formateador = FormateadorSimple()
    servidor = ServidorChat(HOST, PUERTO, sala, formateador)
    servidor.iniciar()