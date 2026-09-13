# Matriz de funciones · beta 7

El catálogo contiene aplicaciones detectadas, no aplicaciones certificadas. Esta matriz complementa los informes ejecutados; no transforma pruebas simuladas en pruebas físicas. No se afirmará ausencia de errores porque transcurra tiempo sin incidentes.

| Función | Cómo se comprueba | Alcance y límite |
| --- | --- | --- |
| TIDAL: reproducir, pausar, pausa repetida, anterior/siguiente | Control real y lectura independiente de estado, barra e identidad sin guardar nombres de canciones; secuencia siguiente → pausa repetida | TIDAL 2.43.2, español, sesión iniciada y música cargada; cambios futuros de interfaz pendientes |
| AIMP: reproducir, pausar, detener, alternar, anterior/siguiente, volumen/silencio | Estado, avance/parada del tiempo, huella del título/duración y volumen antes/después | AIMP 5.40.2703 en esta PC; volumen inicial restaurado |
| Media Player: reproducción, pausa repetida, anterior/siguiente | Dos WAV silenciosos de prueba; Windows publica su estado e identidad de pista | Media Player 11.2606.19.0; Detener no se publica, se ofrece Pausar en Música |
| Windows Media Player Legacy | Apertura real hasta asistente inicial | Pendiente: pide preferencias de privacidad/asociaciones. Se canceló el asistente sin aceptar ni cambiar preferencias |
| Automático con varias apps | Se reproduce fallo de beta6 usando su adaptador original; nueva ruta comprueba sesiones en reproducción y rechaza ambigüedad | Se detectó también una sesión de Opera reproduciendo; se preservó. Esto no certifica todos los sitios web de Opera |
| Volumen/silencio general | Teclas reales y lectura independiente Core Audio; nivel y silencio restaurados | Endpoint predeterminado de esta PC; no se cambiaron dispositivos de sonido |
| Controles en celular | Informe beta7-phone-visible-tests: toques de la app instalada y observación separada en Windows | Debe existir y aprobarse antes de entregar; no se sustituye por llamadas API desde Python |
| Barra AIMP y controles ausentes | Interfaz de producción en Edge: edición durante polling, desaparición de sesión, opciones no admitidas | Transporte aislado; complementa prueba del teléfono |
| Rutinas y edición | Crear/guardar/reordenar; búsqueda sin coincidencias; conservación de app, monitor, modo y política al cambiar tipo de paso | Interfaz real con receptor aislado; ejecución de errores, cancelación y colisiones cubierta por pruebas de cola/adaptador simulado |
| Biblioteca y botones | Edición, guardado, política si ya está abierta, ausencia de app, búsqueda y retirada de botón | El descubrimiento del catálogo no demuestra apertura completa ni funcionamiento de cada app |
| Ventanas | Ventanas reales propias de prueba: mover por ambos monitores, minimizar/restaurar, protección, cierre normal, cierre rechazado y finalización confirmada | No se cierran ventanas del usuario. La prueba no certifica todos los juegos, ventanas elevadas o apps con restricciones |
| Reparación | Regresión de firma, copia incompleta, recuperación, cancelación de tareas; interfaz de confirmación | Repara Eddy Deck, no otras aplicaciones ni Windows. No se reinicia el sistema |
| Energía y bloqueo | Confirmaciones, cuenta atrás y cancelación con adaptador simulado; código de protección despierto existente | No se ejecutan apagado, bloqueo, reinicio ni suspensión reales durante la sesión de mantenimiento |
| Android y reconexión | Instrumentación de APK instalado y recreación de actividad/servicio; restablecimiento de conexión | No prueba datos móviles sin saldo ni todos los fabricantes |
| Instalador y copias | Firma, instalación local, copia limpia aislada, APK con Windows/docs idénticos y SHA-256 del teléfono/escritorio | La copia limpia está en esta misma PC, no es otro equipo físico |
| Datos móviles, otra PC/laptop, ARM, monitor conectado a media sesión, DPI físico | Casos de código/simulación y manual | Pendientes físicos explícitos; no certificados por teoría |

Los informes históricos conservan su versión. Los fallos iniciales de esta campaña se guardan junto a las repeticiones; un error de la herramienta de prueba se distingue de un fallo de producto.
