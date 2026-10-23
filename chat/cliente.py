import socket

PUERTO = 8080


def main():
    host = input("IP del servidor (Enter = 127.0.0.1): ").strip() or "127.0.0.1"
    alias = input("Ingresa tu nombre de usuario (alias): ").strip()

    while not alias:
        alias = input("El alias no puede estar vacío. Intenta otra vez: ").strip()

    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        conexion.connect((host, PUERTO))
        print(f"Conectado a {host}:{PUERTO} como [{alias}].")

        # El protocolo establece que la primera línea enviada es el alias.
        conexion.sendall((alias + "\n").encode("utf-8"))

        print("Escribe mensajes. Usa /salir para terminar.")
        while True:
            texto = input(f"[{alias}]: ").strip()

            if texto.lower() == "/salir":
                break

            if texto:
                # Cada mensaje termina en salto de línea, como espera el servidor.
                conexion.sendall((texto.replace("\n", " ") + "\n").encode("utf-8"))

    except ConnectionRefusedError:
        print(f"No se pudo conectar: no hay un servidor escuchando en {host}:{PUERTO}.")
    except OSError as error:
        print(f"Error de red: {error}")
    finally:
        conexion.close()
        print("Conexión cerrada.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado por el usuario.")
