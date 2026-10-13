"""Cifra una contraseña para .streamlit/secrets.toml.

Pide la contraseña dos veces sin mostrarla y escribe la versión cifrada
(bcrypt, con la herramienta de streamlit-authenticator). Esa es la que va
en el campo password del usuario. La contraseña en claro no se guarda en
ningún sitio.

Uso: python scripts/cifrar_contrasena.py
"""

import logging
import sys
from getpass import getpass

# Al importar la librería, Streamlit avisa de que no hay ninguna app en
# marcha. Aquí no hace falta, así que se silencia mientras se importa.
logging.disable(logging.WARNING)
from streamlit_authenticator import Hasher  # noqa: E402

logging.disable(logging.NOTSET)

sys.stdout.reconfigure(encoding="utf-8")


def main():
    contrasena = getpass("Contraseña: ")
    if not contrasena:
        sys.exit("La contraseña no puede estar vacía.")
    if getpass("Repítela: ") != contrasena:
        sys.exit("Las contraseñas no coinciden.")
    print("\nCopia esta línea en el bloque del usuario en secrets.toml:\n")
    print(f'password = "{Hasher.hash(contrasena)}"')


if __name__ == "__main__":
    main()
