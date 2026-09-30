# Audio y encendido · 2.2.11-beta.13

## Implementación

Windows enumera salidas render activas y consulta volumen/silencio mediante Core Audio. Un auxiliar .NET incluido, EddyDeck-Audio.exe, aplica valores absolutos y comprueba el resultado. Seleccionar salida usa IPolicyConfig, una interfaz no documentada de Windows: se aísla en el auxiliar y se informa si falla. Se cambian Console y Multimedia y se conserva Communications. No se envían teclas globales ni se instala una utilidad externa.

La API de sonido requiere la vinculación habitual y recibos durables. Serializa ajustes con los controles de música. Cada orden incluye el identificador de la salida mostrada, y seleccionar incluye la salida anterior esperada. Una salida desaparecida o una selección externa se rechazan; no se sustituye silenciosamente por otra. No hay reenvío automático tras un tiempo de espera. El volumen no activa el sonido por sí solo.

El celular guarda datos de Wake-on-LAN recibidos únicamente de la PC autenticada en su almacén cifrado, separados por computadora. La interfaz no recibe la MAC. Una pulsación explícita envía tres copias de un paquete mágico de 102 bytes por UDP 9, por una red Wi-Fi/Ethernet física con subred privada coincidente; excluye redes de datos móviles y destinos VPN. Prefiere fijar la red física; si Android lo deniega por la política de VPN, usa un socket normal con la dirección local del Wi-Fi, sujeto a las rutas y restricciones del sistema. No desactiva la VPN. Un límite de frecuencia evita ráfagas y se comprueba la PC seleccionada antes de enviar. No abre puertos de internet, añade cuentas ni modifica BIOS, plan de energía o cortafuegos. La función no permite ejecutar código antes del inicio de Windows.

## Pruebas y límites

Se probaron las cinco salidas activas de esta PC: cambio de salida, nivel absoluto y silencio con un observador Core Audio independiente. Se restauraron salida original, volumen y silencio; comunicaciones se conservó. No se inició reproducción. Las pruebas automatizadas cubren entradas inválidas, desconexión simulada, orden obsoleta, cambios rápidos, aislamiento por PC y formato de paquetes. Los informes beta13 contienen los resultados y separan simulación del Samsung instalado.

No se ha certificado despertar físicamente desde apagado/suspensión, otro router, otra PC, hardware sin Ethernet, BIOS diferentes, direcciones IPv6 solamente ni datos móviles. Wake-on-LAN a través de internet requiere otro equipo local encendido; no está implementado aquí. La detección de hardware no prueba que despierte. La red local debe ser de confianza: los paquetes mágicos estándar no tienen autenticación propia, aunque la app protege y limita sus datos de destino.

La lista puede tardar hasta un segundo en refrescar audio y hasta un minuto en actualizar adaptadores. Aplicaciones con salida propia o audio exclusivo pueden conservar su ruta anterior. No se anuncia funcionamiento infalible ni se convierte esta beta en versión estable.

La primera prueba del Samsung detectó EPERM al fijar la red física con Tailscale. Se corrigió usando la ruta permitida por Android cuando ocurre ese rechazo específico; otros errores no disparan una ruta alternativa. Los informes conservan el intento inicial y la repetición.

La revisión de Claude se intentó una vez y quedó pendiente por sesión OAuth caducada; no hay aprobación externa de esta entrega.

## Referencias

- Microsoft Core Audio: https://learn.microsoft.com/windows/win32/api/endpointvolume/nf-endpointvolume-iaudioendpointvolume-setmastervolumelevelscalar
- Microsoft Wake-on-LAN: https://learn.microsoft.com/troubleshoot/windows-client/setup-upgrade-and-drivers/wake-on-lan-feature
- Tailscale y el intermediario LAN: https://tailscale.com/blog/wake-on-lan-tailscale-upsnap
