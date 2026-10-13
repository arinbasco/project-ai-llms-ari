"""Límite diario de pedidos por usuario.

El contador vive en memoria. La interfaz guarda una sola instancia con
st.cache_resource, compartida por todas las sesiones, así que sobrevive a
las recargas de la página pero se pone a cero si la app se reinicia.
"""

import threading


class ContadorDiario:
    """Cuenta los pedidos de cada usuario en cada día."""

    def __init__(self, maximo):
        self.maximo = maximo
        self._usados = {}
        self._cerrojo = threading.Lock()

    def quedan(self, usuario, dia):
        """Pedidos que le quedan al usuario ese día."""
        with self._cerrojo:
            return max(0, self.maximo - self._usados.get((usuario, dia), 0))

    def reservar(self, usuario, dia):
        """Aparta un pedido si queda alguno. Devuelve False si no queda.

        Se reserva antes de llamar al redactor para que dos sesiones del
        mismo usuario no pasen a la vez del máximo. Si el redactor falla, hay
        que devolverlo con liberar().
        """
        with self._cerrojo:
            # Los días anteriores ya no sirven.
            self._usados = {clave: n for clave, n in self._usados.items() if clave[1] == dia}
            usados = self._usados.get((usuario, dia), 0)
            if usados >= self.maximo:
                return False
            self._usados[(usuario, dia)] = usados + 1
            return True

    def liberar(self, usuario, dia):
        """Devuelve un pedido reservado que no llegó a hacerse."""
        with self._cerrojo:
            usados = self._usados.get((usuario, dia), 0)
            if usados > 0:
                self._usados[(usuario, dia)] = usados - 1
