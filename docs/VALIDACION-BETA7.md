# Validación de Eddy Deck 2.2.5-beta.7

Esta campaña parte de una carencia real de cobertura: abrir programas no comprobaba sus controles multimedia. Se amplía la prueba a efectos observables de TIDAL, AIMP y Media Player, botones de la interfaz, edición de rutinas y volumen. El listado de Biblioteca no equivale a probar todas las aplicaciones. Consulta MATRIZ-FUNCIONES-BETA7.md para el alcance por función.

## Fallos reproducidos y cambios

- La ruta automática de beta6 podía pausar TIDAL mientras Media Player seguía reproduciendo. Se ejecutó ese adaptador original sobre las apps reales para demostrarlo. Ahora se consulta también Windows Media Sessions y se exige elegir un destino si varias reproducen. Un error de consulta no se trata como lista vacía ni se deriva a otra app.
- TIDAL podía terminar de cargar la pista después de una pausa inmediata y seguir reproduciendo. Se conserva beta7-tidal-next-pause-initial-race.json. El controlador espera cambio de pista y estabilidad antes de responder; la repetición de tres ciclos está en beta7-tidal-next-pause-regression.json.
- La búsqueda sin coincidencias de un paso conservaba un appId oculto. Se vacía y exige selección válida. Cambiar el tipo de paso perdía campos sin guardar, también por una envoltura antigua del editor: ahora conserva app, URL compatible, diseño, reproductor y política de apertura.
- Una app ausente no permitía abrir su editor para quitar el botón. Ahora tiene un editor de retirada y sincronización. Una sesión multimedia ausente conserva su identidad visible y desactiva controles incompatibles. Se protege la barra de AIMP mientras se edita frente a renders periódicos.
- Silencio general se etiqueta como «Silenciar / activar». Los controles que el reproductor no publica se desactivan; cuando no dispone de Detener se ofrece Pausar. Teclas de Windows es un destino explícito sin verificación.

## Evidencias y criterio de entrega

Los informes beta7 se entregan en Informes y en EddyDeck-Pruebas-2.2.5-beta.7.zip. package_evidence.py exige regresión Python, UI, multimedia real, controles del Samsung instalado, prueba Android, integridad de instalación y copias. Los informes de fuente actual incluyen hashes; no se atribuyen horas históricas a este código.

beta7-media-audit-live.json comprueba música real mediante los adaptadores; beta7-rapid-media.json prueba secuencias rápidas adicionales. beta7-system-volume-live.json lee Core Audio independientemente y restaura volumen/silencio. beta7-visible-ui-tests.json usa HTML/JS de producción con transporte simulado. beta7-ui-tests.json y beta7-ui-regressions.json complementan flujos cotidianos y fallos inyectados. beta7-windows-controls.json se limita a procesos de prueba propios; no acredita todas las apps. Los informes de teléfono e instalación separan toques físicos, instrumentación y copias.

Una repetición inicial del ensayo multimedia encontró otra sesión de Opera reproduciendo: se corrigió la precondición del ensayo para exigir ambigüedad y preservar esa sesión. El primer lector SMTC de TIDAL podía observar metadatos atrasados; el lector independiente usa ahora la identidad de su footer accesible. Se conservan fallos iniciales, sin convertirlos retrospectivamente en aprobados.

## Arquitectura y revisión

EddyDeck-Media.exe consulta Windows.Media.Control; no requiere IA, red ni nuevas cuentas. El destino es un hash del identificador de app publicado por Windows; se resuelve de nuevo por orden y rechaza duplicados. No permite ejecutar comandos arbitrarios. Pausa/reproducción se comprueban por estado; cambio de pista por metadatos. Se acotan las esperas y no se repiten órdenes inciertas. Esto no convierte al reproductor externo en una transacción: una intervención simultánea o una app que informe mal su estado sigue siendo un límite.

TIDAL conserva validación de HWND/PID/fecha/ruta y UI Automation. AIMP comprueba identidad y ahora espera el estado para reproducción/pausa/detener. Ambos helpers quedan en el manifiesto firmado del instalador y en su reparación. No se afirma firma Authenticode individual. Windows se compila antes de Android; el APK contiene los mismos Windows y documentos.

Claude Code revisa una copia saneada de solo lectura. Su dictamen original y la resolución de Codex se conservan en los informes de beta7, indicando cualquier disponibilidad degradada. No se atribuye una revisión recibida si falló el servicio.

## Límites y respaldo

Pruebas en esta PC: AIMP 5.40.2703, TIDAL 2.43.2 y Media Player 11.2606.19.0. Windows Media Player Legacy requiere configuración inicial de privacidad/asociaciones; se canceló sin aceptar y no se certifica su reproducción. Opera se detectó como sesión multimedia; no se certifican todos sus sitios ni se alteró su reproducción para aislar pruebas.

Siguen pendientes datos móviles con saldo, otra PC/laptop física, ARM64, cambios físicos de monitor/DPI, otros idiomas/versiones y restricciones de cuenta/red. No se realizaron apagados, reinicios, bloqueos ni suspensiones reales. No hay despertar remoto ni garantía de ausencia total de fallos.

Escritorio y teléfono conservan entregas anteriores y verifican copias por SHA-256. Drive se mantiene privado y se verifican nombre, tamaño, carpeta y permisos; el hash procede del original local, no de descargar de nuevo cada archivo. El índice final se entrega aparte para evitar una referencia circular. Código e informes compartibles excluyen claves, tokens y vinculación; las claves originales permanecen en private del proyecto. VALIDACION-BETA6.md conserva el alcance histórico.


## Resolución de la revisión y ensayos adicionales

Claude devolvió NEEDS_CHANGES sin bloqueadores de seguridad declarados. Codex agrupó sesiones con el mismo identificador en una única opción desactivada y ambigua, corrigió las combinaciones inválidas del editor y añadió pruebas de concurrencia de solicitudes. La coordinación detectó además nombres de reproductor interpolados sin escape: se corrigieron Inicio y Música y se probó que el texto no crea HTML. No se atribuye a Claude aprobación de estos cambios posteriores.

AIMP también presentó el cruce siguiente → pausa: se preserva beta7-rapid-media-initial-aimp-failure.txt. Ahora espera identidad de pista y estado estable; una primera corrección asumía reproducción tras Anterior, pero AIMP puede conservar la pausa o volver al inicio. Se corrigió y se repitieron tres ciclos en AIMP y Media Player.

Si dos pistas seguidas exponen exactamente la misma identidad y no hay otra señal comprobable, puede mostrarse un resultado no confirmado aunque haya ocurrido el cambio. Se conserva ese límite en vez de afirmar éxito sin observación. La revisión C# es estática; las pruebas reales de esta PC se informan por separado.

La repetición final encontró otra transición de TIDAL: la etiqueta indicaba reproducción antes de avanzar la barra. Se conserva beta7-media-audit-tidal-transition-failure.txt. Ahora el salto exige también avance temporal estable; espera hasta 6.5 segundos y el subproceso está limitado a 12. La auditoría posterior del código actual cubrió entre 22 y 23 comprobaciones multimedia, según las sesiones abiertas; las 190 pruebas Python y 24 comprobaciones específicas de interfaz complementan los 29 flujos UI existentes. Estos conteos no significan cobertura total.

La prueba física también mostró que una actualización de estado podía reemplazar el selector de reproductor mientras su menú nativo estaba abierto. Se extiende la conservación de controles enfocados a selectores/campos y se añade una regresión explícita. Un fallo previo distinto de la herramienta pulsó un botón oculto bajo la navegación: la prueba ahora desplaza el control por encima de esa barra antes de tocarlo; ese fallo de coordenadas no se atribuye a Eddy Deck.

Al guardar el manual desde Android se observó la navegación inferior fuera de la pantalla. Un nombre largo de sesión ensanchaba Inicio; se acota su contenedor y se trunca visualmente el nombre sin alterar el destino. Se añaden pruebas de anchura de Inicio con identificadores largos a 320 y 412 px, además del regreso real del selector de archivos. CSS y HTML se incorporan a los hashes de las pruebas actuales.
