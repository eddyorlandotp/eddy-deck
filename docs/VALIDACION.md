# Validación · Eddy Deck 2.2.9-beta.11

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
