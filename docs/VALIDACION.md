# Validación de beta 13 · 2.2.11-beta.13

Alcance nuevo: salidas de sonido, volumen absoluto y encendido LAN desde Android. Los resultados de beta 12 y anteriores que aparecen debajo son históricos. Los informes `beta13-*` se generan con las fuentes y los binarios de esta entrega; no se reciclan como pruebas nuevas los de otras versiones.

- Audio real: cinco salidas de Windows, selección de Console/Multimedia, volumen/silencio leídos por observador independiente; restauración del sonido y conservación de Communications.
- Interfaz simulada: barra de Inicio/Música, envío al soltar, coalescencia, cambio de PC, salida desconectada, menú visual y botón de encendido sin receptor.
- Android: paquete mágico, rechazo de direcciones, subredes y PC obsoleta; almacenamiento por identidad dentro del almacén cifrado. Ver informe instrumentado y comprobación visible del APK final.
- No se ha apagado ni suspendido Windows para certificar el despertar físico. La emisión de la señal, el ajuste del controlador y una recepción UDP no prueban un arranque.
- Claude: revisión pendiente por autenticación caducada, sin aprobación atribuida. Codex integra y verifica localmente.

Consulta AUDIO-ENCENDIDO-BETA13.md y el manual separado para compatibilidad y uso. La publicación exige informes actuales, integridad instalada, APK final y copias verificadas.

---

# Validación · Eddy Deck 2.2.10-beta.12

## Beta 12: conexión que se repara sola

Esta versión responde a un incidente real: Defender puso Eddy Deck en cuarentena y un acceso directo saltó a una copia antigua con otra identidad. El análisis y el diseño están en [RESILIENCIA-BETA12.md](RESILIENCIA-BETA12.md).

Pruebas de esta entrega (los resultados exactos están en los informes `beta12-*` de `.build`):

- **Python:** 269 pruebas en total, 25 de ellas nuevas en `tests/test_resilience.py`. Incluyen:
  - la reproducción del salto del acceso directo: el acceso antiguo resuelve a `EddyDeck-previous-*` y el nuevo no;
  - la desactivación de copias anteriores, también con una copia en uso;
  - el orden de versiones, idéntico al del comprobador C#;
  - la preferencia de inicio que sobrevive al borrado del acceso;
  - la salida intencional limitada a la sesión de Windows;
  - la autorreparación con pasos independientes;
  - el rechazo de un comprobador distinto al instalado;
  - la redirección de copias antiguas;
  - las causas registradas por el supervisor y su umbral de 45 s.
- **C#:** la tabla de decisiones del vigilante (`tests/WatchdogChecks.cs`), compilada con `Watchdog.cs`.
- **Android:** 70 aserciones instrumentadas en el Samsung, 7 de ellas nuevas. Cubren:
  - PC encendida con el receptor caído;
  - rechazo desde la PC sin ping adicional;
  - un rechazo en loopback que no afirma que la PC esté encendida;
  - Tailscale apagado;
  - otra identidad;
  - la identidad guardada, que nunca cambia.

  Las pruebas con transporte simulado no envían paquetes.
- **Instalación real sobre beta 11:**
  - Se conservaron `deck.json`, `devices.json`, `server.crt` y `server.key` (hash idéntico) y la vinculación del celular.
  - La tarea del vigilante quedó registrada con nivel limitado.
  - 27 copias anteriores quedaron desactivadas.
  - Defender no registró detecciones nuevas.
- **Supervisión real:**
  - 10 minutos de sondeo por segundo sin anomalías (latencia máxima de `/health`, 0,03 s; latido máximo, 1,5 s).
  - Primer arranque tras instalar, con el vigilante registrándose en ese momento: 5 minutos sin anomalías después de los primeros 5 s de arranque (latido máximo, 1,6 s). El registro del vigilante no bloquea la interfaz.
- **Pruebas reales de punta a punta en esta PC y el Samsung:**
  1. **Receptor terminado de forma abrupta** (como un antivirus o un fallo): el vigilante lo reabrió y `/health` volvió en 6,4 s.
  2. **Salida intencional:** el vigilante registró `user-exit` y no abrió nada.
  3. **Diagnóstico en el celular con el receptor detenido:**
     - con la app ya conectada, el aviso superior mostró "está encendida y responde, pero Eddy Deck no está abierto" y el indicador pasó a "Sin conexión";
     - al abrir la app desde cero, la pantalla de reconexión mostró la misma causa.
  4. **Ejecutable ausente** (cuarentena simulada renombrándolo): el vigilante registró `missing`, mostró el aviso y no reinstaló nada. Después se restauró el archivo.
  5. **Recuperación:** tras reinstalar, el celular reconectó con la misma huella.

Pendiente:

- Un bloqueo intermitente previo, que la beta 11 registró 67 veces sin causa, todavía no se ha observado con el nuevo registro de causa.
- La revisión independiente de Codex: no hubo cuota disponible durante esta entrega (se reanuda a partir del 23/09, 17:27). Se hizo una autorrevisión que corrigió cuatro defectos antes de entregar:
  - la marca de salida por código 0;
  - la reactivación de una tarea desactivada por el usuario;
  - los avisos tras una desinstalación;
  - la causa que no se mostraba porque `extended.js` sustituye `load()`.
- La firma Authenticode.
- El reporte de falso positivo a Microsoft, que requiere la cuenta del usuario.
- Un reinicio completo de Windows con el disparador de inicio de sesión del vigilante.

## Beta 11

Xbox registra un identificador para abrirse y otro para su ventana. Se añadió la correspondencia exacta, comprobada en su manifiesto instalado, sin asociar otras aplicaciones o widgets de ese paquete.

Si una aplicación bloquea su ventana principal con un aviso o diálogo, Eddy Deck lo señala y conserva esa decisión pendiente. No intenta mover ni cerrar esa ventana desde los controles normales.

Esta entrega amplía la revisión a los cinco apartados de la interfaz, el catálogo completo de esta PC, rutinas, música, procesos auxiliares, persistencia y actualización desde GitHub. Sigue siendo beta: un conjunto finito de pruebas no demuestra ausencia de errores en todas las aplicaciones o combinaciones.

## Correcciones

Los selectores personalizados se aplican también a Música y conservan su diálogo durante la actualización de estado. Los cambios inválidos del panel o que fallan al guardar se revierten en memoria. La música tiene espera acotada; una rutina puede cancelar mientras espera ese recurso. Cancelar durante el último paso conserva el efecto ya enviado y registra la cancelación. Si desaparece el reproductor seleccionado, no se envía una tecla global a otro programa.

Una apertura que requiere administrador ya no puede dejar indefinidamente ocupada la cola: la llamada nativa está aislada, tiene plazo y se cancela con su operación. Los auxiliares de apertura, activación y música están ligados a la vida del receptor; las aplicaciones abiertas por el usuario permanecen independientes. Blood Strike permitió encontrar un bloqueo real del antiguo camino de apertura; su ejecutable ahora informa la necesidad de permiso manual.

El comprobador descarga paquetes desde GitHub Releases, verifica firma, tamaño, hash, origen y contenido antes de ofrecer su instalación. Drive se conserva exclusivamente como respaldo privado. Consulta [ACTUALIZACIONES-GITHUB.md](ACTUALIZACIONES-GITHUB.md).

## Evidencia y alcance

- La regresión Python y los casos cotidianos están en `beta11-core-tests.json`. Incluyen fallos de disco, edición de rutinas en cola, cancelación, veinte sesiones simuladas, destinos desaparecidos y muerte del receptor con auxiliares activos.
- `beta11-pickers-tests.json` y `beta11-visual-tests.json` separan interacción web y geometría visual. `beta11-phone-walkthrough.json` registra exclusivamente lo observado mediante toques y capturas nuevas en el Samsung instalado.
- `beta11-updater-tests.json` cubre la implementación C# con manifiestos firmados de prueba, versiones, cancelación y archivos maliciosos. La descarga pública real se registra aparte cuando la publicación completa está disponible.
- `beta11-catalog-live.json` clasifica cada entrada del catálogo. Ventana observada, activación, minimización, cambio de tamaño y limpieza tienen resultados independientes. Una pantalla de carga, un proceso o una entrada descubierta no certifican el funcionamiento interno de un juego.
- `catalog-beta11-crud.json` prueba crear, editar, guardar y eliminar botones de cada entrada en un perfil aislado; no representa aperturas físicas.
- `beta11-monitor-tests.json` prueba geometría y desconexión simulada en mil topologías; `beta11-http-tests.json`, solicitudes inválidas, límites y conexiones incompletas. Ninguno sustituye una segunda PC real.
- Los informes de instalación, instrumentación Android y copias identifican la versión y los archivos exactos. Las pruebas anteriores se conservan con su número de beta y no cuentan como repetidas en esta entrega.

Claude realizó una revisión de solo lectura de una instantánea de 129 archivos. Sus hallazgos y la resolución de Codex se conservan separados. El dictamen inicial pidió cambios; no se presenta como aprobación de código posterior ni como prueba en hardware.

## Limpieza y límites

El recorrido conserva las sesiones anteriores y registra las ventanas creadas por la prueba mediante identificador, proceso y fecha de creación. Si una aplicación pide iniciar sesión, permisos o confirmar un documento, ese caso se detiene. Los juegos pueden sustituir su pantalla inicial por otra ventana: se inspeccionan también las ventanas tardías. Cerrar una ventana puede dejar un reproductor en la bandeja; se registra por separado.

Siguen pendientes datos móviles disponibles y otra red exterior, reinicio completo de Windows, otra computadora física, ARM, conexión/desconexión física de monitores y todas las funciones internas de programas de terceros. No se prueba apagar o reiniciar esta PC mientras se trabaja. La cancelación no deshace un efecto que Windows ya recibió. No se garantiza despertar una PC suspendida; el receptor mantiene la vigilia según la opción configurada.

El manual para uso diario está en [MANUAL-USUARIO.md](MANUAL-USUARIO.md); el recorrido y su metodología en [RECORRIDO-BETA11.md](RECORRIDO-BETA11.md). Windows se compila antes de Android, que lleva el mismo instalador. Los resultados definitivos están en los informes de la entrega; cualquier caso pendiente permanece visible.
