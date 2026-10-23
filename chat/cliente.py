import socket
import threading

PUERTO = 8080


def recibir_mensajes(conexion, conectado):
    """Escucha al servidor en segundo plano."""
    while conectado["activo"]:
        try:
            datos = conexion.recv(1024)
            if not datos:
                print("\nEl servidor cerró la conexión.")
                conectado["activo"] = False
                break

            # Limitación pendiente: recv() puede contener mensajes parciales
            # o varios mensajes juntos; aquí se imprime todo lo recibido.
            print("\r" + datos.decode("utf-8", errors="replace").rstrip())
        except OSError:
            conectado["activo"] = False
            break


def main():
    host = input("IP del servidor (Enter = 127.0.0.1): ").strip() or "127.0.0.1"
    alias = input("Ingresa tu nombre de usuario (alias): ").strip()

    while not alias:
        alias = input("El alias no puede estar vacío. Intenta otra vez: ").strip()

    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conectado = {"activo": False}

    try:
        conexion.connect((host, PUERTO))
        conectado["activo"] = True

        # El servidor interpreta la primera línea como el alias.
        conexion.sendall((alias + "\n").encode("utf-8"))
        print(f"Conectado a {host}:{PUERTO} como [{alias}].")
        print("Escribe mensajes. Usa /salir para terminar.")

        hilo = threading.Thread(
            target=recibir_mensajes,
            args=(conexion, conectado),
            daemon=True,
        )
        hilo.start()

        while conectado["activo"]:
            try:
                texto = input(f"[{alias}]: ")
            except (KeyboardInterrupt, EOFError):
                print("\nCerrando el chat...")
                break

            if not conectado["activo"]:
                break
            if texto.strip().lower() == "/salir":
                print("Saliendo del chat...")
                break
            if texto.strip():
                try:
                    conexion.sendall(
                        (texto.replace("\n", " ") + "\n").encode("utf-8")
                    )
                except OSError:
                    print("No se pudo enviar el mensaje: se perdió la conexión.")
                    break

    except ConnectionRefusedError:
        print(f"No se pudo conectar: no hay un servidor escuchando en {host}:{PUERTO}.")
    except OSError as error:
        print(f"Error de red: {error}")
    finally:
        conectado["activo"] = False
        try:
            conexion.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conexion.close()
        print("Conexión cerrada.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado por el usuario.")
