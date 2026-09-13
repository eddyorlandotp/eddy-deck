# Validación de Eddy Deck 2.2.0-beta.2

Entrega personal para Windows 11 y Android. Las pruebas reducen riesgos concretos; no son una garantía de ausencia de fallos.

## Entorno y separación de evidencias

PC Windows 11 Pro x64, compilación 26200, con dos monitores; Samsung Galaxy S24 Ultra SM-S928B, Android 16/API 36. Los informes de sistema compartibles omiten nombre de usuario, serie, tokens y claves. No se dispone de otra laptop/PC ni de Windows ARM. El celular no tiene datos móviles disponibles.

Esta entrega separa pruebas sobre hardware real, simulaciones, ensayos de duración, errores del montaje de pruebas y pendientes. Un catálogo o un proceso no equivalen a una aplicación completamente probada. La beta 1 se conserva en VALIDACION-BETA1.md; su barrido de aperturas no se presenta como una repetición completa de esta beta.

## Pruebas automatizadas de esta entrega

| Área | Resultado y alcance |
| --- | --- |
| Lógica Python, API, TLS y recuperación | 98 pruebas aprobadas; autenticación, deduplicación, pausa/cancelación, instantáneas, admisión coordinada, escritura fallida, perfiles extensos, integridad y recuperación |
| Android real con datos de prueba aislados | 58 comprobaciones aprobadas: cifrado, varias PCs, reintentos, PC equivocada, límites de tareas, exportación grande, servicio y TLS real |
| Interfaz en Edge | 15 comprobaciones aprobadas; anchos 1280, 412 y 320, sin errores JavaScript; colas, políticas, versiones, recibos y manual desconectado |
| Solicitudes hostiles contra receptor aislado | 90 comprobaciones aprobadas: JSON inválido o profundo, tipos incorrectos, tamaños, importación grande, TLS incompleto y recuperación |
| Ventanas Windows creadas para la prueba | 20 comprobaciones aprobadas: identificación, protección, movimiento en ambos monitores, minimizar/restaurar, cierre normal y finalización del proceso propio |
| Instalación en carpetas aisladas | Cinco comprobaciones aprobadas: copia limpia, ausencia de claves de esta PC, destinos de accesos directos, caché de reparación y actualización que conserva datos. El adaptador de accesos directos está controlado; no sustituye otra PC física |
| Comprobador Windows independiente | 12 paquetes de prueba aceptados/rechazados según correspondía; ninguno de sus ejecutables de prueba se ejecutó |
| Panel y catálogo | 135 aplicaciones con crear/editar/persistir/releer/eliminar botones y política de ventana; datos aislados, sin abrir 135 apps |
| Pantallas simuladas | 1,000 topologías, 17,969 comprobaciones; una a cinco pantallas, coordenadas negativas, geometrías, ausencia y ambigüedad |
| Panel de tamaño máximo por cantidad | 200 botones y 50 rutinas con 24 pasos; 1,400 referencias distintas. Catálogo simulado de 1,501 apps; exportación restringida a referencias usadas |
| Historial extenso | 100,000 recibos históricos; reinicio y repetición de una orden antigua sin volver a ejecutarla. 30 operaciones nuevas: mediana 18.863 ms, máximo 21.341 ms en esta PC |
| Recuperación local del perfil | Cuatro casos con el EXE empaquetado: validar copias sin modificar botones, vínculos ni certificado. Pruebas adicionales inyectan perfil corrupto y fallo de escritura |

Las cifras cuentan escenarios o aserciones de tipos distintos; no se suman para anunciar miles de funcionalidades probadas. Los transportes simulados de interfaz no reemplazan las pruebas Windows/Android reales.

## Ensayos prolongados

Se ejecutaron dos ensayos aislados de colas, rutinas, cancelación, recibos y reinicios. No enviaron operaciones físicas a otras aplicaciones.

- **Ensayo A:** 7200.0 segundos, 600 ciclos, 6620 solicitudes, 2400 envíos duplicados controlados, 600 cancelaciones antes de ejecutar y 20 reinicios del receptor simulado. Errores inesperados: 0.
- **Ensayo B:** 4800.0 segundos, 400 ciclos, 4413 solicitudes, 1600 envíos duplicados controlados, 400 cancelaciones antes de ejecutar y 13 reinicios. Errores inesperados: 0.

- **Núcleo Python definitivo:** 600.0 segundos, 50 ciclos, 551 solicitudes y 1 reinicios, sin errores y con todos los hashes de módulos Python sin cambios durante el recorrido.

Los ensayos se solapan: no se suman como horas consecutivas de uso. Sus informes guardan hashes del código cargado al comenzar. Se desarrolló parte de la beta mientras corrían: A detectó cambios posteriores en companion\core.py, companion\desktop.py, companion\diagnostics.py, companion\installer.py, companion\jobs.py, companion\layout.py, companion\supervisor.py; B en companion\core.py. El ensayo B mantuvo el código de cola y control de ventanas durante su ejecución; los cambios posteriores del núcleo se validaron con la batería final. No se presenta la duración completa como prueba de cada línea añadida después.

**Conexión real del Samsung:** Observación aprobada. Duración 2400.3 segundos, 81 muestras, servicio inactivo en 0 muestras y mayor antigüedad observada de una petición autenticada de 26.0 segundos. Fue una observación pasiva con USB y alimentación disponibles; no representa horas bajo ahorro de batería ni una prueba desde otra red. El JSON conserva el estado de pantalla y ruta observados por muestra.

## Comprobaciones físicas y recuperación

- **Calculadora:** nueva apertura, derecha en ventana, vertical maximizada, mitades, minimizar/restaurar y rechazo de pantalla ausente. Se cerró solo la ventana creada para esa prueba.
- **AIMP:** lectura de estado y escritura del mismo volumen; se conservaron volumen y reproducción. No se cambió de canción ni se validó una sesión completa de todos los reproductores.
- **Ventanas controladas:** una ventana aceptó cierre normal y otra simuló cambios pendientes rechazándolo. Se obtuvo «necesita atención» y después se finalizó solo el proceso creado para la prueba. La restauración conservó su geometría anterior. Las ventanas previas ajenas a la prueba se conservaron.
- **Reparación real de archivos:** se alteró únicamente LEEME.md de Eddy Deck después de respaldarlo. El Samsung detectó la modificación, solicitó la reparación y el comprobador repuso el archivo; volvió el receptor. Botones, vínculos y certificado conservaron exactamente sus hashes. La prueba pertenece a una compilación candidata de esta beta; el informe de entrega verifica después la integridad de los binarios finales.
- **Wi-Fi y USB:** se apagó Wi-Fi y se retiró el túnel USB. El manual siguió accesible sin conexión. Después de restaurar Wi-Fi se observó una petición autenticada nueva en 5 segundos desde el inicio de la observación, sin vincular de nuevo.
- **Android detenido y reabierto:** se observó reconexión en 2 segundos desde el inicio de la observación y el servicio de primer plano volvió. Wi-Fi y el túnel USB se restauraron.
- **Exportaciones y ciclo de pantalla:** La recreación real de Activity con una exportación quedó pendiente: el Samsung se bloqueó durante ese recorrido y la actividad no tuvo foco. No se cuenta como aprobada. Sí pasaron la recreación del gestor de exportaciones y la finalización de escrituras aceptadas al cerrar sus ejecutores.

Los 5 y 2 segundos son medidas de esos recorridos, no un tiempo máximo garantizado para cualquier red. Las pruebas conservaron las seis tarjetas personales y la identidad del equipo.

## Incidencias de las pruebas y cómo se trataron

La primera ventana de prueba con «documento pendiente» solo rechazaba un motivo de cierre de WinForms; se corrigió el fixture para rechazar todos los cierres normales y se repitió la prueba. No se utilizó un documento del usuario para provocar ese diálogo.

Una instalación de prueba en una ruta profunda encontró WinError 206 por la longitud de nombres internos de licencias. Se conservaron todos los textos con rutas cortas y un índice de procedencia; la repetición de instalación y actualización pasó. Un primer adaptador COM del propio test también falló y fue sustituido por un adaptador controlado de accesos directos; no se presenta ese adaptador como prueba de COM real.

Una ejecución inicial del ensayo HTTP observó un cierre de transporte al enviar un cuerpo sobredimensionado. Se separó la comprobación de cabeceras (413 antes de enviar el cuerpo) de cinco envíos completos, que pueden recibir 413 o cierre de transporte; se verifica además que no ocurrió ninguna acción física y que el servicio se recupera. Esto evita clasificar una desconexión de rechazo como una orden aceptada.

Una prueba Android de cantidad de eventos tuvo que considerar el nuevo evento de redescubrimiento. Se corrigió el punto de referencia y la batería completa pasó. El intento de recreación con pantalla bloqueada no se contó como éxito; se conserva su salida inicial por separado.

## Aplicaciones: historial y pendientes

CATALOGO-PRUEBAS.md conserva el barrido de la beta 1: 71 aperturas con ventana observada; 46 con cuatro cambios verificados y 25 parciales, además de exclusiones y recorridos pendientes. Esta beta repitió las 135 pruebas de botones y las regresiones físicas de Calculadora, AIMP y ventanas propias. No repitió ni afirma el uso completo de todas las aplicaciones.

Inicio de sesión, juegos, anticheat, compras, mensajes, grabaciones, controladores y todas las funciones internas de cada app siguen fuera de la certificación. Un programa puede pedir actualizarse o imponer su posición/tamaño. En casos ambiguos se elige la ventana manualmente o se informa del límite.

## Compatibilidad y límites pendientes

- Datos móviles u otra red externa real: pendiente por falta de datos. La conexión por Tailscale se verificó con la conectividad disponible; no se presenta como control mundial ya ensayado.
- Segunda PC/laptop Windows 11, equipos corporativos, Windows ARM y permisos/firewall distintos: pendientes físicos. El paquete x64 incluye su runtime y bibliotecas; ARM depende de emulación y no se certificó.
- Conectar/desconectar monitores físicamente, cambiar DPI real, sesión sin monitor y escritorio remoto: se probaron modelos lógicos, no esas modificaciones físicas.
- Una pantalla fija se guarda por su nombre lógico de Windows, no por una identidad física EDID permanente. Al cambiar de PC, dock o cableado se debe revisar esa selección; Principal e izquierda/derecha se resuelven de nuevo.
- Apagar, reiniciar, suspender, bloquear e inicio después de un reinicio completo de Windows: no se ejecutaron. Se probaron validación, confirmación, cuenta atrás y cancelación con adaptadores aislados. No hay encendido remoto ni desbloqueo de Windows.
- Android bajo ahorro de batería, suspensión profunda o días sin abrirlo: no se garantiza que el sistema mantenga el servicio. El ensayo con alimentación no sustituye esas condiciones.
- Protección de ventanas: dura mientras la ventana y el receptor existan. No es un bloqueo de Windows ni puede deshacer una acción ya iniciada.
- Drive: descarga privada en el navegador y comprobación posterior del paquete. No es un actualizador automático autenticado contra Google.
- No se realizó una auditoría externa ni un programa público de recompensas. Las pruebas adversariales se restringen a este software y receptores aislados.
- Un sistema congelado, disco defectuoso/lleno, almacén cifrado dañado, permisos denegados o VPN expirada puede necesitar intervención local. No siempre es posible guardar un informe si falla el almacenamiento.

Referencia para acceso por internet y sus requisitos: https://tailscale.com/docs/concepts/what-is-tailscale . La PC debe estar encendida, despierta, con sesión iniciada, Eddy Deck y VPN activos; ambos equipos necesitan internet.

## Entrega reproducible y evidencias

Los archivos beta2-*.json y beta2-*.txt de Informes contienen resultados individuales; catalog-beta2-crud.json detalla las 135 entradas. beta2-release-verification.json compara código, instalador, recursos Android e instalación final. beta2-final-device-verification.json compara el APK instalado y las copias del teléfono cuando se completa ese recorrido.

Windows se compila antes de Android porque el APK incluye ese Windows. package_release.py valida documentación y prepara código, APK, ZIP Windows independiente, paquete completo y hashes. publish_desktop.py verifica las copias y conserva versiones anteriores. El registro de publicación de Drive contiene los identificadores y tamaños verificados de los archivos privados.

Los paquetes e informes excluyen private, tokens y datos de vinculación. Las claves para futuras firmas se conservan en el proyecto original y requieren un respaldo privado separado. El manual, arquitectura y matriz de seguridad explican mantenimiento y recuperación sin IA.

Las copias finales del teléfono pueden entregarse por USB con verificación SHA-256. Ese resultado no se convierte en una prueba del selector nativo de archivos: el informe del dispositivo declara el método usado. La carpeta temporal de una instalación fallida se conservó dentro de .build porque la revisión automática bloqueó su eliminación; queda fuera de todos los paquetes.
