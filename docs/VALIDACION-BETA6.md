# Validación de Eddy Deck 2.2.4-beta.6

Esta versión corrige la pausa de TIDAL que Eddy reportó desde Inicio y Música. La beta anterior devolvía «Control enviado a Windows» aunque TIDAL seguía reproduciendo. Una petición aceptada no demostraba que el reproductor hubiese obedecido; las pruebas anteriores no cubrían ese caso real. Se reprodujo el fallo en TIDAL 2.43.2 y se sustituyó la ruta por control accesible directo de su reproductor.

## Corrección y alcance

EddyDeck-Tidal.exe verifica HWND, PID, hora de creación y ruta de TIDAL. Busca el reproductor footerPlayer y sus botones de accesibilidad en español o inglés. No cierra TIDAL, no cambia el foco ni usa clics por coordenadas. Pausar y detener significan quedar en pausa. Reproducir es explícito; alternar resuelve su intención una sola vez. El resultado de pausa/reproducción exige dos observaciones del estado deseado. Se toleran transiciones breves del árbol accesible sin volver a pulsar. El subproceso tiene un plazo de ocho segundos; un resultado incierto no se repite automáticamente ni se desvía a otro reproductor.

La selección automática consulta un estado fresco antes del efecto. Si TIDAL y AIMP reproducen simultáneamente, pide elegir el destino. La pantalla puede mostrar un estado de hasta 1.5 segundos de antigüedad; la ejecución vuelve a consultar. El volumen y silencio de TIDAL en Eddy Deck son los de Windows y ahora se indican como tales, también en rutinas. AIMP conserva su volumen directo.

## Evidencias de esta versión

Los resultados ejecutados se entregan en Informes y EddyDeck-Pruebas-2.2.4-beta.6.zip; las pruebas que preceden a la instalación no se presentan como pruebas del APK instalado.

- beta6-core-tests.json: suite Python completa, ligada por SHA-256 al código actual, incluido el helper C#; cubre destino ambiguo, caché atrasada, errores, ausencia de TIDAL, JSON inválido, plazo y ausencia de reintentos.
- beta6-tidal-live-tests.json: reproductor TIDAL real mediante la ruta Deck, perfil de pruebas aislado. Pausa, reproducción, repetición de pausa, detener, duplicado de la misma solicitud, rutina de reproducción seguida de pausa, ventana minimizada e identidad cambiada. Un lector independiente comprueba que la barra avanza al reproducir y queda quieta al pausar. Se restaura la posición original y se deja la música pausada.
- beta6-tidal-ui-tests.json: HTML/JavaScript de producción en Edge con transporte simulado. Verifica Inicio, selector de tres reproductores, acciones explícitas, etiqueta de pausa y alcance del volumen. No equivale a tocar el teléfono.
- beta6-tidal-phone-tests.json: prueba separada de botones reales del Samsung, con beta6 instalada en ambos equipos, y observación independiente del estado y barra de TIDAL.
- beta6-android-installed-tests.json: instrumentación de conexión y tres ciclos del servicio/actividad instalados. Se vuelve a abrir Eddy Deck al finalizar.
- beta6-release-verification.json y beta6-final-device-verification.json: integridad del paquete, helper, instalador contenido en APK, copias del teléfono y conservación de perfil/vinculación.

El primer lector auxiliar de progreso no pudo ejecutarse por la política de scripts de Windows PowerShell. Se reemplazó por un lector C# independiente sin modificar esa política. Otra repetición detectó una confirmación intermitente al minimizar; una lectura posterior detectó que dos consultas podían cruzarse con el cambio de nombre del mismo botón. Se lee cada nombre una sola vez y se confirma un estado estable. Se conservan los registros iniciales de fallo y las repeticiones, sin convertirlos retrospectivamente en aprobados.

## Revisión independiente

Claude Code revisó una copia de solo lectura y entregó NEEDS_CHANGES por la etiqueta de silencio de TIDAL que ocultaba su efecto global. Codex corrigió el texto visible y el destino explícito, y añadió regresión. Se conserva el dictamen original, junto con la resolución del integrador. La coordinación también señaló la caché de selección automática; ahora se exige lectura fresca. Los cambios posteriores y las pruebas son responsabilidad de Codex; no se atribuye una segunda aprobación que no se recibió.

## Instalación, respaldo y límites

Windows se compila antes de Android. EddyDeck-Tidal.exe queda incluido en el manifiesto firmado y la reparación del receptor; no se afirma una firma Authenticode individual. El APK contiene ese mismo paquete y manual. Escritorio y celular conservan versiones anteriores; sus copias se verifican por SHA-256. Drive se mantiene privado y se verifican nombre, tamaño, carpeta y permisos. Los hashes de Drive proceden de los originales locales, no de descargar cada archivo de nuevo. El índice de Drive se entrega por separado para evitar referencias circulares.

Se comprobó TIDAL 2.43.2 en este Windows, con interfaz en español. Se admiten etiquetas en inglés por código, sin ensayo de otra instalación física. Otros idiomas, cambios futuros en el árbol accesible, pantallas de inicio de sesión, carga de música, restricciones de cuenta/red y un TIDAL ejecutado como administrador pueden impedir el control; se muestra un error. La ventana entre lectura y acción no es una transacción con TIDAL; una intervención simultánea externa puede cambiar el estado. No se promete que nunca falle.

Siguiente/anterior se envían directamente al botón de TIDAL, pero el cambio de canción se marca como no verificado. No se confunde pausa con cierre ni se certifican otros reproductores por estas pruebas. Los informes no incluyen títulos de canciones. La protección de ventanas afecta mover/cerrar, no los controles de reproducción, como ocurre con AIMP.

VALIDACION-BETA5.md conserva la evidencia anterior: no se atribuyen sus horas o resultados al código nuevo. Siguen pendientes datos móviles con saldo, otra PC/laptop física, ARM64, cambios físicos de monitor/DPI y escenarios de otros fabricantes. No se realizaron apagados, reinicios, bloqueos ni suspensiones reales. No hay despertar remoto ni conmutación automática verificada entre asistentes.
