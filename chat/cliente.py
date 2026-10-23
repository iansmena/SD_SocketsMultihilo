import socket       # Comunicación por red (sockets TCP)
import threading    # Para crear el hilo que recibe mensajes en segundo plano

# Se importan las reglas comunes definidas en protocolo.py
from protocolo import LectorMensajes, enviar_mensaje

COMANDO_SALIR = "/salir"    # Texto que el usuario escribe para abandonar el chat


class ClienteChat:
    """
    Gestiona la conexión con el servidor y la interacción con el usuario por consola.
    No da formato a los mensajes: envía texto plano y el servidor le agrega el alias.
    """

    def __init__(self, host: str, puerto: int):
        self._host = host           # IP del servidor
        self._puerto = puerto       # Puerto del servidor
        self._socket = None         # Se crea al conectar
        self._conectado = False     # Bandera compartida por los dos hilos
        self._alias = ""            # Nombre del usuario en el chat

    def _prompt(self) -> str:
        """Texto que aparece antes de lo que escribe el usuario, por ejemplo '[Ian]: '."""
        return f"[{self._alias}]: "

    def iniciar(self) -> None:
        """Pide el alias, se conecta, lanza el hilo de recepción y atiende la escritura."""
        # 1. Pedir el alias hasta que el usuario escriba algo (strip() quita espacios sobrantes)
        while not self._alias:
            self._alias = input("Ingresa tu nombre de usuario (alias): ").strip()

        try:
            # 2. Crear el socket TCP y conectarse al servidor
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self._host, self._puerto))
            self._conectado = True

            # 3. Según el protocolo, lo primero que se envía es el alias
            enviar_mensaje(self._socket, self._alias)
            print(f"\nConectado a {self._host}:{self._puerto} como [{self._alias}].")
            print(f"Escribe tus mensajes y presiona Enter. Escribe {COMANDO_SALIR} para salir.\n")

            # 4. Lanzar el hilo que recibe mensajes en segundo plano
            hilo_recepcion = threading.Thread(target=self._recibir_mensajes, daemon=True)
            hilo_recepcion.start()

            # 5. El hilo principal se queda leyendo el teclado
            self._enviar_mensajes()

        except ConnectionRefusedError:
            print(f"No se pudo conectar: no hay un servidor escuchando en {self._host}:{self._puerto}.")
        except OSError as error:
            print(f"Error de red: {error}")
        finally:
            self.cerrar_conexion()

    def _recibir_mensajes(self) -> None:
        """Se ejecuta en el hilo secundario: muestra todo lo que llega del servidor."""
        lector = LectorMensajes(self._socket)
        while self._conectado:
            try:
                mensaje = lector.leer()
            except OSError:
                mensaje = None    # El socket se cerró o se perdió la red
            if mensaje is None:
                # Solo se avisa si el usuario no pidió salir (si no, el aviso sobra)
                if self._conectado:
                    print("\n\nSe perdió la conexión con el servidor. Presiona Enter para salir.")
                    self._conectado = False
                break
            # \r regresa el cursor al inicio de la línea para escribir el mensaje sobre el prompt
            print(f"\r{mensaje}")
            # Se vuelve a mostrar el prompt para que el usuario siga escribiendo
            # end="" evita el salto de línea; flush=True lo muestra de inmediato
            print(self._prompt(), end="", flush=True)

    def _enviar_mensajes(self) -> None:
        """Se ejecuta en el hilo principal: lee el teclado y envía cada línea."""
        while self._conectado:
            try:
                texto = input(self._prompt())    # Espera a que el usuario escriba y presione Enter
            except (KeyboardInterrupt, EOFError):
                # Ctrl+C (o Ctrl+Z / Ctrl+D) cierra el cliente de forma ordenada
                print("\nCerrando el chat...")
                break
            if not self._conectado:
                break    # El servidor se cayó mientras el usuario escribía
            if texto.strip().lower() == COMANDO_SALIR:
                print("Saliendo del chat...")
                break
            if texto.strip():
                try:
                    enviar_mensaje(self._socket, texto)
                except OSError:
                    print("No se pudo enviar el mensaje: se perdió la conexión.")
                    break

    def cerrar_conexion(self) -> None:
        """Cierra el socket de forma ordenada. Se puede llamar aunque nunca se haya conectado."""
        self._conectado = False
        if self._socket is None:
            return
        try:
            # shutdown avisa al servidor que esta conexión termina
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass    # La conexión ya estaba cerrada; no hay nada que avisar
        self._socket.close()
        print("Conexión cerrada.")


# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    PUERTO = 8080    # Debe coincidir con el puerto del servidor
    try:
        # Si el usuario solo presiona Enter, se usa 127.0.0.1 (la misma computadora)
        host = input("IP del servidor (Enter = 127.0.0.1): ").strip() or "127.0.0.1"
        cliente = ClienteChat(host, PUERTO)
        cliente.iniciar()
    except KeyboardInterrupt:
        # Ctrl+C antes de conectarse (mientras pide la IP o el alias)
        print("\nCancelado por el usuario.")