# Reconexión · Beta 9

## Identidad estable

El fallo observado no era solo una IP distinta: Windows podía entregar dos carpetas AppData a la misma aplicación según su proceso de origen. Una tenía el certificado vinculado al celular y la otra el certificado servido después de reiniciar. Microsoft documenta esta redirección en [el comportamiento de aplicaciones empaquetadas](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes).

`companion/storage.py` usa `%USERPROFILE%\.eddydeck`; comprueba la ruta física y migra una única copia antigua en una transacción. Si encuentra varias configuraciones posibles, conserva ambas y pide resolver cuál corresponde, sin generar silenciosamente otra identidad. En este equipo se eligió la copia cuyo certificado coincide con el almacenado por Android. No se incluyen certificados, llaves o dispositivos en paquetes compartibles. La copia del registro de operaciones usa la API backup de SQLite y cierra ambos manejadores antes de renombrar el directorio.

## Recuperar la ruta sin cambiar la confianza

`companion/network.py` obtiene IPv4 de GetAdaptersInfo y usa DNS solo como alternativa si la API no está disponible. El receptor publica direcciones actuales a dispositivos autenticados. Android conserva varias rutas, también la última dirección privada VPN si el adaptador desaparece temporalmente. El descubrimiento usa Wi-Fi/Ethernet, se limita en tiempo y cantidad de candidatos y exige un heartbeat con el certificado original antes de recordar una ruta. Un anuncio falso por UDP no sustituye la identidad. Si Android rechaza elegir Wi-Fi directamente mientras una VPN está activa (EPERM, reproducido en el Samsung), el descubrimiento conserva la ruta de red elegida por el sistema y los mismos límites y comprobaciones de identidad.

Las comprobaciones de conexión tienen tiempo reducido; el recorrido tiene un presupuesto monotónico. La orden se transmite una sola vez después de comprobar la ruta. La pérdida de respuesta es ambigua y se resuelve mediante recibos, no volviendo a transmitir automáticamente. Se vuelve a comprobar la PC seleccionada antes de enviar.

## Internet

La LAN funciona sin servicios externos. El acceso desde otra red usa Tailscale: no se añadió un servidor nuevo, no se abrieron puertos en el router y no se creó un protocolo criptográfico propio. Sus [direcciones privadas](https://tailscale.com/docs/concepts/ip-and-dns-addresses) permanecen estables mientras el dispositivo siga registrado; eliminarlo/reinstalarlo puede cambiarlas. Ambos equipos deben tener internet y estar conectados a la misma red privada. No basta con que Eddy Deck esté abierta si Tailscale está detenido.

La VPN siempre activada de Android permite al sistema mantener/iniciar Tailscale. No se habilita el bloqueo del resto del tráfico. No sustituye una cuenta válida, internet disponible o las políticas de batería y red del sistema. Cambiar a otra VPN interrumpe esta ruta. No existe garantía de disponibilidad absoluta.
