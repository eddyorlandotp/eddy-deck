# Validación de Eddy Deck 2.2.2-beta.4

Informe técnico de 2.2.2-beta.4. Las pruebas previas a compilar terminaron; la verificación de instalación y copias se registra después en los JSON del paquete de evidencias. El control de publicación exige también que termine la observación posterior a instalar.

## Entorno y criterio de prueba

Windows 11 Pro x64, compilación 26200, dos monitores; Samsung Galaxy S24 Ultra SM-S928B, Android 16/API 36, conectado por USB y Wi-Fi. No hay datos móviles disponibles ni una segunda PC física.

La sesión activa empezó el 12 de septiembre de 2026 a las 22:34:15.725 UTC, después de verificar la pantalla del teléfono. La interrupción anterior no cuenta como trabajo. El mínimo solicitado de 150 minutos se cumple a las 01:04:15.725 UTC del 13 de septiembre. Los ensayos que se ejecutan en paralelo no suman horas consecutivas.

Las cifras cuentan escenarios o aserciones de tipos distintos. No se suman para anunciar miles de funcionalidades, ni convierten una simulación en una prueba física. MANUAL-USUARIO.html y MANUAL-USUARIO.md explican las funciones; FIABILIDAD-BETA4.md explica el diseño.

## Regresiones ejecutadas sobre el candidato

| Área | Resultado y alcance |
| --- | --- |
| Python | 146 pruebas aprobadas (incluidas nueve de bloqueo de publicación): intervalos independientes de la hora, autorización, cancelaciones, recibos, cola, perfiles, arranque parcial, datos ilegibles, recursos y cierre con disco lleno |
| Interfaz habitual en Edge | 16 comprobaciones aprobadas, anchos 1280/412/320, sin errores JavaScript |
| Regresiones nuevas de interfaz | 13 comprobaciones aprobadas: avisos de energía, texto escapado, edición abierta, reloj desajustado, música, volumen, confirmación/cancelación y consultas concurrentes o de otra PC |
| Ventanas reales desechables | 20 comprobaciones aprobadas en ambos monitores: proteger, mover, minimizar, restaurar, cierre normal, rechazo por cambios pendientes y finalización del proceso creado para la prueba |
| HTTP aislado | 90 comprobaciones aprobadas de entradas malformadas, límites, importaciones y clientes TLS incompletos; ninguna operación física |
| Historial extenso | 100,000 recibos conservados; repetición tras reinicio sin ejecutar de nuevo. Treinta órdenes nuevas: mediana 7.667 ms y máximo 9.107 ms en este recorrido |
| Energía Windows nativa | Seis comprobaciones sobre un hilo propio: adquirir, mantener y liberar SYSTEM_REQUIRED; sin cambiar el plan de energía ni solicitar mantener encendido el monitor |
| Volumen Windows real | Bajó de 0.260375381 a 0.24000001 y subió a 0.26; se restauraron exactamente el nivel original y el silencio en el mismo dispositivo de audio |
| Plazos con reloj real | 73.24 segundos de recorrido: las cuatro acciones de energía llegaron al adaptador falso después de 15.032–15.034 segundos, una sola vez. Cancelar a los 0/2/10 segundos no envió la acción |
| Catálogo actual | 136 entradas con crear/editar/persistir/releer/eliminar aprobados, sin abrir esas aplicaciones; catalog-beta4-crud.json |
| Geometría de pantallas | 1,000 topologías simuladas y 17,969 aserciones aprobadas sobre layout.py actual; de una a cinco pantallas, destinos ausentes/ambiguos y coordenadas negativas |

No se cambió de canción. No se bloqueó, suspendió, apagó ni reinició Windows para esas pruebas de energía. Los resultados históricos están en VALIDACION-BETA2.md y CATALOGO-PRUEBAS.md; salvo la matriz de geometría repetida que se identifica arriba, no se presentan como recorridos repetidos de beta 4.

## Ensayos de duración

Resultados cerrados antes de compilar. Al registrar este cierre habían transcurrido 151.1 minutos efectivos desde la comprobación inicial de pantalla.

| Ensayo | Duración observada | Resultado e informe |
| --- | --- | --- |
| Continuidad del código inicial | 9,000.0 s | Aprobado; beta3-resumed-soak-tests.json |
| Rutinas del candidato anterior a las últimas correcciones | 7,200.0 s | Aprobado; beta4-soak-tests.json |
| Observación de Windows y Samsung instalados | 8,040.4 s | Completada; 1 incidencia de instrumentación revisada; beta4-installed-observation.json |
| Clientes TLS incompletos sobre fuentes definitivas | 1,800.5 s | Aprobado; beta4-network-soak-tests.json |
| Recibos concurrentes y reapertura de SQLite | 1,800.0 s | Aprobado; beta4-concurrent-receipts-soak.json |
| Rutinas sobre todo el código Python definitivo | 5,400.0 s | Aprobado; beta4-soak-final-source-tests.json |
| Recreaciones de Activity en el Samsung | 3,581.466 s; 120 ciclos | 960 comprobaciones aprobadas; beta4-lifecycle-soak-tests.json |

Después de instalar se exige una observación adicional limpia de 90 segundos (beta4-postinstall-observation.json), además de las comprobaciones de APK, integridad, instalación y copias. Se ejecutan después de esta compilación y sus resultados se incorporan a Informes; no se sustituyen por las observaciones de beta 3.

Los ensayos de rutinas usan datos aislados y un adaptador de Windows falso. Guardan los hashes de los módulos cargados; los cambios posteriores figuran en sourceChangedDuringRun. El ensayo final debe corresponder a todos los módulos actuales. Los recorridos que continuaron mientras se corregía el código no prueban por toda su duración los cambios añadidos después.

El primer ensayo TLS completó 1,800.5 segundos, 120 ciclos y 1,321 lecturas sin fallos. Se conserva en beta4-network-initial-soak-tests.json porque core.py y jobs.py cambiaron después de iniciarlo. La repetición de la tabla usa las fuentes definitivas.

El ensayo adicional de recibos utiliza ocho invocadores simultáneos y efectos contados en memoria. Repite identificadores, rechaza contenido cambiado después del original y comprueba que el mismo identificador pertenece a espacios separados por dispositivo. Reabre SQLite con las órdenes terminadas y verifica que no vuelvan a ejecutarse. No simula un reinicio de proceso en mitad de una orden ni errores deliberados de la acción. Cuenta los envíos concurrentes aparte de las invocaciones auxiliares. Claude revisó este montaje y emitió READY para ese alcance; el piloto corto permanece separado del resultado de duración.

La observación pasiva verifica salud, peticiones autenticadas recientes, identidad TLS, servicio Android y protección de pantalla. Conserva las anotaciones de mantenimiento y las incidencias. Las métricas de memoria e hilos Android son observaciones, no una demostración de ausencia de fugas durante días.

La repetición Android terminó con 120 ciclos y 960 comprobaciones en 3,581.466 segundos. Se observó después la aplicación abierta, su servicio y una petición autenticada nueva, sin una incidencia adicional. Corría la APK beta 3 instalada. Los siete archivos Java de producción coinciden byte por byte con la copia archivada de beta 3 (beta4-android-source-comparison.json); la interfaz y el manifiesto de beta 4 sí cambian, por lo que el APK actualizado tendrá además su comprobación de instalación y un recorrido breve propio.

El primer ensayo Android quedó incompleto a los 45 ciclos y 1,324.319 segundos: otra aplicación pasó al primer plano y Android terminó el proceso instrumentado con la causa «finished inst». Se conserva beta4-lifecycle-incomplete-first.txt; no cuenta como una hora aprobada ni como caída espontánea de la app de producción. El montaje repetido espera si falta el primer plano entre ciclos, sin robarlo a otra aplicación.

La observación inicial registró una muestra con servicio Android detenido a las 23:24:27.675 UTC; el receptor Windows y su identidad seguían sanos. A las 23:24:57.984 UTC ya había servicio, primer plano y petición autenticada nueva. beta4-observation-incident-review.json relaciona ambas muestras con la instrumentación terminada. El informe original conserva su incidencia y no se presenta como una corrida limpia. Después de instalar se exige una observación adicional de 90 segundos sin incidencias imprevistas, junto con comprobaciones activas de instalación, recreación y reconexión.

## Teléfono y conexión reales

La primera actualización instalada mantuvo la pantalla en primer plano durante 37.1 segundos con el tiempo normal de apagado en 15 segundos. Se tomaron siete muestras despiertas; al salir al inicio de Android dejó de mantenerla encendida y al volver recuperó la protección. El tiempo de apagado quedó exactamente como estaba. No se cambió el PIN ni se desactivó el bloqueo.

En beta 3 instalada se desactivó Wi-Fi dejando el USB existente: hubo una petición autenticada nueva por USB en 7.51 segundos. Después de activar Wi-Fi y retirar brevemente el túnel USB, volvió por Wi-Fi en 4.01 segundos. Se restauraron Wi-Fi y el túnel USB; botones, vínculos y certificado conservaron sus hashes. El ensayo de recreaciones de Activity continuó durante el cambio.

Son medidas de este recorrido, no tiempos máximos garantizados. No representan datos móviles ni otra ciudad. El acceso desde otra red requiere internet y Tailscale activo en ambos equipos; Windows debe estar despierto, con sesión iniciada y Eddy Deck ejecutándose.

## Defectos corregidos y recuperación

- Cambiar la fecha/hora podía alterar plazos. Se usan intervalos monotónicos; las fechas históricas siguen siendo informativas.
- El panel podía omitir un aviso durante una edición o descartar un refresco forzado al coincidir con un sondeo. Conserva la edición y espera una consulta nueva. Una respuesta de la PC anterior no sustituye el estado de la actual.
- Una segunda instancia sin interfaz podía recuperar el Journal mientras otra lo usaba. Se adquiere la propiedad de la carpeta antes de construir Deck y se reconoce el receptor anterior activo.
- Un JSON ilegible o una identidad incompleta podía terminar sin explicación visible. Se conservan los datos y se limpian los recursos antes del diálogo. Headless devuelve el error a quien lo invocó.
- Si no inicia el primer o segundo hilo de servidor, sus sockets sin iniciar se cierran directamente, sin esperar un bucle inexistente.
- Si el disco falla al registrar cancelaciones de cierre, la cola igualmente se detiene. El siguiente inicio marca lo pendiente como interrumpido y no lo repite.
- Fallar al cerrar un recurso no impide intentar liberar los demás. Un receptor cerrado rechaza nuevas acciones; no puede deshacer de forma general una operación física que ya empezó.
- Un editor antiguo no puede recrear silenciosamente una rutina que se eliminó mientras estaba abierto.

Al retomar la sesión se observó una diferencia entre el certificado servido por un proceso antiguo y el certificado original en disco. Se reiniciaron únicamente los procesos verificados de Eddy Deck y volvió a servirse la identidad original. Botones, vínculos y certificado conservaron sus hashes. La causa no se estableció: el reinicio no demuestra haber eliminado su causa. Informe: beta3-resume-identity-recovery.json.

## Revisión independiente y montaje de pruebas

Claude Code revisó copias saneadas con permisos de lectura; Codex integró y ejecutó pruebas. Los informes preservan NEEDS_CHANGES, sus resoluciones, la base revisada y los archivos posteriores. El repaso de arranque/TLS/refrescos emitió READY para su snapshot, y el repaso separado de cierre resistente a fallos también emitió READY.

La auditoría documental pidió corregir tres discrepancias: el mínimo de la prueba final, la fila de observación posterior a instalar y el relato del ensayo Android interrumpido. Su revisión posterior emitió READY sobre las tres resoluciones, sus ocho pruebas de publicación y la matriz de pantallas repetida. Los ensayos prolongados todavía estaban en ejecución en aquel snapshot: ese dictamen no acredita su finalización. No es una certificación externa ni un programa público de recompensas.

Una prueba de salida abrupta inicialmente detenía el lanzador del entorno virtual, dejando vivo al intérprete dueño del bloqueo. Se corrigió para salir desde ese intérprete con os._exit y pasó la liberación por Windows. Era un fallo del montaje, no evidencia de un bloqueo retenido tras terminar el dueño real.

En el montaje UI se corrigió la espera de un marcador de autenticación fresco, el consumo de la respuesta de prueba y la lectura de un contador con unidad «s». Los resultados iniciales se conservan separados de los defectos de producto. No se publican tokens, claves ni marcadores privados.

## Aplicaciones y pendientes

El historial de beta 1 conserva 71 aperturas con ventana observada: 46 con cuatro cambios de ventana y 25 parciales. Una ventana puede ser un lanzador, inicio de sesión o actualización. No demuestra el funcionamiento completo de un juego o programa. Sesiones, anticheat, permisos, compras, mensajes, grabaciones y hardware no se validan automáticamente.

- Datos móviles, otra red física y restricciones del operador: pendientes por falta de datos disponibles.
- Segunda PC/laptop, Windows ARM, cambio de dock y conexión/desconexión física de monitores: pendientes. Las simulaciones de geometría no las sustituyen.
- Ahorro de batería, suspensión profunda de Android, tapa cerrada o batería crítica pueden interrumpir el servicio.
- No hay encendido, despertar ni desbloqueo remoto. La protección de Windows no anula una suspensión manual.
- Reparar Eddy Deck repone sus archivos o reinicia su conexión; no repara todo Windows ni cierra otras aplicaciones.
- Drive permite descargar una copia privada y comprobarla después. No hay actualización silenciosa autenticada contra Drive.
- Un fallo de almacenamiento o permisos puede requerir intervención local; si no se puede escribir, tampoco se garantiza guardar un informe.
- No se verificó un relevo automático de escritura entre servicios de IA. Los archivos y guías permiten continuar sin depender de esta conversación.

## Entrega e integridad

Windows se compila antes de Android, que incorpora su instalador. La entrega reúne código, manual, informe técnico, APK, Windows, paquete completo y evidencias, conservando versiones previas en escritorio, teléfono y Drive privado. Los resultados posteriores a compilar están en los informes release-verification, final-device-verification y postinstall-observation de beta 4. Publicar las evidencias requiere que estos ensayos de duración hayan terminado; este documento no sustituye la comprobación real de los paquetes instalados.

release-verification compara archivos firmados, fuentes, documentación, recursos incrustados e instalación. final-device-verification comprueba por SHA-256 el APK y las copias del teléfono; declara si se copiaron por USB, sin presentarlo como prueba del selector nativo.

El índice de Drive se entrega separado del ZIP de pruebas para evitar una verificación circular. La comprobación remota acredita nombres, tamaños y permisos privados; los hashes corresponden a archivos locales, no a un cálculo independiente en Drive. Las claves de firma permanecen en private del proyecto y quedan fuera de los paquetes compartibles.

El entorno observado de compilación está en beta4-build-environment.json y se explica en ENTORNO-COMPILACION.md. El control de evidencias exige tanto solicitar como cumplir 5,400 segundos para la prueba de fuentes definitivas; una corrida corta no pasa por llevar hashes correctos.

Una novena regresión de publicación comprueba que una versión futura no utilice solo los informes históricos: debe actualizar explícitamente su matriz de ensayos. Es posterior a la revisión documental de ocho casos y queda incluida en la ejecución final de 146 pruebas.

El control final de instalación utiliza 90 segundos de observación y pruebas activas del APK y la reconexión. Sustituye la espera pasiva de 600 segundos que figuraba en la revisión documental anterior; esa revisión conserva su alcance y fecha originales.
