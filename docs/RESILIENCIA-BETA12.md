# Resiliencia · Beta 12

## Incidente que motivó esta versión

Observado en esta PC el 22 de septiembre de 2026:

1. **19/09, 14:37.** Microsoft Defender clasificó `EddyDeck.exe` como `Behavior:Win32/DefenseEvasion.A!ml`, una detección de comportamiento por aprendizaje automático. Puso el ejecutable en cuarentena, terminó el supervisor y el receptor, y eliminó los accesos de Inicio y del menú. El código no contiene nada que evada defensas. Se considera un falso positivo, favorecido por un binario PyInstaller sin firma ni metadatos que abre aplicaciones, simula teclas, crea accesos de inicio y ejecuta auxiliares ocultos.
2. **20/09.** El acceso del escritorio había sido creado con `WScript.Shell`, que guarda datos de rastreo. Al faltar su destino, Windows lo resolvió hacia `EddyDeck-previous-…` del 11/09. Esa copia usa otra carpeta de datos y otra identidad TLS, así que Android la rechazó correctamente. En el registro aparece "Solicitud interrumpida" cada ~30 s.
3. La red no fue la causa. El celular estaba en otro Wi-Fi y alcanzaba la PC por Tailscale.

La reproducción está en `tests/test_resilience.py::Shortcuts`. Un acceso creado a la antigua salta a la carpeta anterior; uno de beta 12 conserva su ruta.

## Cambios

| Área | Cambio | Archivo |
| --- | --- | --- |
| Accesos directos | Se crean con `IShellLink` y `SLDF_FORCE_NO_LINKTRACK`, `SLDF_DISABLE_LINK_PATH_TRACKING` y `SLDF_DISABLE_KNOWNFOLDER_RELATIVE_TRACKING`. Se leen sin `Resolve`. Se reescriben al instalar y en cada arranque de la copia instalada. Un acceso del escritorio borrado por el usuario no se recrea. | `companion/resilience.py`, `installer.py` |
| Copias anteriores | Tras cada actualización, y en cada arranque, `EddyDeck-previous-*\EddyDeck.exe` pasa a `EddyDeck.exe.anterior`. No se borra nada. Una copia en ejecución se omite y se reintenta después. La recuperación usa los ZIP firmados de `recovery`. | `resilience.disable_stale_copies` |
| Versión antigua abierta a mano | Si la copia ejecutada no es la instalada y es más antigua que ella, abre la instalada y termina. Las opciones de instalación y comprobación nunca se redirigen. | `supervisor.entry` |
| Preferencia de inicio | Se guarda en `preferences.json`, así un antivirus que borre el acceso no la pierde. Se deduce una sola vez del acceso existente. | `resilience.startup_wanted` |
| Vigilante | Tarea por usuario *Eddy Deck - Vigilante*: al iniciar sesión y cada 5 minutos, con nivel limitado y sin administrador. Ejecuta `Rescue\EddyDeck-Compatibilidad.exe --watchdog`. Solo se registra si ese comprobador es idéntico al de la versión instalada. | `resilience.register_watchdog`, `installer/Watchdog.cs` |
| Salida intencional | **Salir** (código 0) escribe `user-exit.json`. El vigilante lo respeta hasta el siguiente arranque de Windows y lo compara con `GetTickCount64`. | `supervisor.py`, `desktop.py` |
| Supervisor | Antes reiniciaba tras 3 comprobaciones fallidas (~6 s). Ahora exige ≥ 3 fallos y ≥ 45 s seguidos, y registra la causa (`heartbeat-stale`, `health-503`, `health-TimeoutError`…). La beta 11 acumuló 67 reinicios de este tipo, cada uno una desconexión del celular. | `supervisor.liveness_problem`, `unresponsive` |
| Diagnóstico Android | Si ninguna ruta responde, hace como máximo dos pings ICMP de ≤ 1,5 s a las rutas guardadas. Windows descarta en silencio el TCP a un puerto cerrado (medido: `nc` expira; el ping responde). | `Connections.diagnose` |
| Interfaz | La pantalla de reconexión y el aviso superior muestran la causa. La notificación de segundo plano usa un texto breve. | `ui/app.js`, `ConnectionService.java` |
| Metadatos | `EddyDeck.exe` declara empresa, producto, descripción y versión. | `scripts/build_windows.py` |

Las causas que muestra Android:

| Tipo | Condición | Mensaje |
| --- | --- | --- |
| `receiver-down` | La PC rechaza el puerto o responde al ping | PC encendida; abre Eddy Deck o revisa Seguridad de Windows |
| `vpn-off` | Sin VPN activa en el teléfono y con ruta Tailscale guardada | Activa Tailscale |
| identidad | TLS con otra huella | Respondió otra copia de Eddy Deck; no se enviaron órdenes |
| `unreachable` | Nada responde | PC apagada, suspendida o sin Tailscale |

Un rechazo en `127.0.0.1` no cuenta, porque sin USB esa ruta no dice nada de la PC. El diagnóstico nunca cambia la identidad guardada ni reenvía órdenes.

## Qué hace y qué no hace el vigilante

| Estado | Acción |
| --- | --- |
| Salida intencional en esta sesión | Nada |
| Instalación en curso (`Local\EddyDeck-Installation`) | Nada |
| `/health` responde "Eddy Deck" | Nada |
| Falta toda la carpeta del programa (desinstalado) | Nada, sin avisos |
| Falta solo `EddyDeck.exe` (típico de una cuarentena) | Aviso cada 6 h como máximo; el clic abre el historial de protección. **No reinstala.** |
| Proceso instalado activo sin responder | Espera al supervisor; tras ~30 min avisa |
| Sin proceso | Abre `EddyDeck.exe --tray`, hasta 3 veces por hora; después avisa y se detiene |

Si una persona desactiva la tarea en el Programador de tareas, Eddy Deck respeta esa decisión y no la reactiva. Solo **Salir** marca una salida intencional: un código de salida 0 por sí solo no basta, porque el receptor también sale con 0 cuando encuentra otra copia activa.

Reinstalar sin intervención un archivo que el antivirus retiró sería, precisamente, eludir una defensa. Esa decisión es del usuario.

## Límites

- Un antivirus puede volver a marcar Eddy Deck. Lo que reduce de verdad el riesgo es firmar con Authenticode, con un certificado de pago, o que Microsoft reciba el reporte de falso positivo. La exclusión de carpeta la decide el usuario; Eddy Deck no modifica Defender.
- La tarea programada y el vigilante son otro mecanismo de persistencia. Tras instalarlos se comprobó que Defender no registró detecciones nuevas, pero no hay garantía futura.
- El paquete ya no incluye los reenviadores `api-ms-win-*`, que PyInstaller dejó de copiar. Windows 11, el único sistema admitido, los integra.
- El ping puede estar bloqueado por el firewall en redes locales públicas. Entonces el mensaje cae en "No encuentro tu PC", que no es incorrecto, solo menos específico.
- Sigue sin existir despertar remoto, y Tailscale sigue siendo necesario fuera de la red local.
