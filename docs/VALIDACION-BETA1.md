# Validación de Eddy Deck 2.1.0-beta.1

11 de septiembre de 2026. Windows 11 Pro x64, dos monitores y Samsung Galaxy S24 Ultra SM-S928B con Android 16/API 36. Beta para uso personal, con pruebas y límites documentados; no garantiza ausencia absoluta de fallos.

## Pruebas del producto

- **56 pruebas Python/HTTP/TLS aprobadas.** Autenticación, PIN de un solo uso/caducidad/límite, token local rechazado por red, revocación, URLs y perfiles inválidos, comandos arbitrarios rechazados, persistencia, recibos tras reinicio, deduplicación, concurrencia, cola limitada, cancelación, rutinas que detienen o continúan ante errores y monitores ausentes/ambiguos. También reparación, supervisor obsoleto, límite de reintentos, informes sin secretos, segundo inicio que no interrumpe trabajos, agregar/deduplicar ejecutables portables y fallos de disco sin botones fantasma ni bloqueo permanente del receptor.
- **33 comprobaciones Android aprobadas en el Samsung real.** Keystore/AES-GCM, migración, dos perfiles independientes, cambio/olvido de PC, órdenes de una PC anterior rechazadas, reapertura, destinos privados/VPN, TLS real con rechazo de huella falsa y soporte con historial limitado. El informe sigue disponible cuando falla el almacén cifrado y no lo borra. Las preferencias de prueba están aisladas; no representan otra PC física.
- **Interfaz en Edge aprobada.** Rutina de tres pasos, editar/guardar/releer diseños, ejecución simulada, pregunta de monitor solo cuando corresponde, música sin esa pregunta, desconexión/reconexión, exportación del diagnóstico y confirmación de reparación. Vistas 1280×1000 y 412×915 sin errores JavaScript ni desbordamiento horizontal.
- **Calculadora real:** apertura nueva, derecha en ventana, vertical maximizada, mitad de pantalla, minimizar, restaurar, pantalla ausente rechazada y alternativa explícita a la principal. Se corrigieron la identificación UWP al minimizar y la restauración desde maximizada; la repetición completa pasó.
- **Catálogo:** inventario inicial de 149 entradas. Se eliminaron herramientas del sistema y accesos obsoletos. `CATALOGO-PRUEBAS.md` registra apertura, movimiento, compatibilidad parcial y pendientes por entrada. Una ventana inicial no prueba las funciones internas de una app.
- Resultado final del barrido y repeticiones: **71 aperturas con ventana identificada**, 46 con cuatro cambios verificados y 25 parciales; 2 ventanas anteriores conservadas, 1 caso con varias ventanas, 12 aperturas sin ventana identificable dentro del plazo, 9 variantes de lanzador compartido, 40 recorridos manuales pendientes por sesión/hardware/permisos y 14 entradas excluidas. Catálogo válido final: **135** entradas, todas con prueba de botones aprobada.
- **Botones:** crear, editar, persistir, releer y eliminar por HTTP para cada entrada del catálogo válido, usando datos temporales sin alterar el perfil personal. `catalog-beta-crud.json` contiene cada resultado. Una primera ejecución demasiado rápida recibió correctamente el límite de 180 acciones/minuto; la repetición respeta ese límite.
- **AIMP directo:** lectura real del estado y escritura del mismo volumen mediante su adaptador, verificando que volumen y reproducción se conservaron. No se inició ni cambió una canción para esta comprobación.

## Recuperación real

- **Reparar app del celular:** ejecutado desde Inicio; interfaz y servicio vuelven conservando la PC vinculada y la preferencia de segundo plano.
- **Reparar receptor de la PC:** ejecutado y confirmado desde el Samsung. Cambió el proceso de Windows y volvió la conexión. Perfil e identidad de vinculación conservados.
- **Terminación inesperada:** se terminó solo el proceso hijo de Eddy Deck, verificando ejecutable, PID, creación y supervisor. El supervisor sobrevivió y recuperó una conexión autenticada en unos **10 segundos**. No había rutinas ni acciones de energía pendientes en esa prueba.
- **Guardar informe:** exportación real desde Android a `Descargas/EddyDeck-informe.json`, con diagnóstico de ambos equipos y sucesos de reparación/conexión. Sin token, PIN, URL privada ni clave. Android conserva 100 sucesos; Windows rota su registro y conserva hasta 100 informes.
- Las órdenes interrumpidas no se repiten automáticamente. La cola y recibos duraderos indican los resultados inciertos. Las pruebas de concurrencia usan adaptadores controlados; no abren simultáneamente todos los juegos.
- No se garantiza un informe si el disco está lleno/inaccesible. El registro auxiliar no convierte una acción ya realizada en falso fallo por no poder escribirlo. Un fallo del registro duradero previo a una orden impide aceptarla con normalidad.

## Instalación y conexión

- Instalación Windows por usuario, sustitución verificada y carpeta anterior recuperable. Inicio automático activado mediante acceso directo `--tray`; sigue siendo opcional y ocurre al entrar a la sesión.
- Android actualizado con la misma firma, seis botones personales conservados, notificaciones permitidas y servicio activo. Interfaz incluida en el APK, sin CDN ni IA.
- Tailscale oficial y ambos equipos en su red privada. Se recibieron solicitudes autenticadas del Samsung por su dirección VPN con la conectividad disponible. No se abrieron puertos del router ni se desactivó el firewall.
- Android lleva el paquete Windows para otra PC. Los informes de entrega registran la exportación por selector de archivos y la igualdad SHA-256 con el recurso del APK. No incluye claves ni vinculación de esta PC.
- La versión anterior también superó reapertura tras detener Android y 28 segundos en segundo plano sin el túnel USB, con una solicitud autenticada nueva. No demuestra supervivencia indefinida al ahorro de batería.

## Prueba desde otra red: pendiente

Tailscale permite conectar por internet. La PC debe estar encendida, despierta, con sesión iniciada, Eddy Deck y Tailscale activos. El Samsung necesita internet y su VPN activa. La distancia geográfica no es el requisito; la conectividad de ambos sí lo es.

Se apagó temporalmente Wi-Fi y se retiró USB: no llegó una petición autenticada en 48 segundos, aunque el servicio Android seguía activo. Eddy confirmó que **no tiene datos móviles disponibles**. Se restauraron Wi-Fi y USB. La prueba completa desde datos móviles u otra red externa sigue pendiente; no se presenta como acceso mundial ya probado.

Referencia: https://tailscale.com/docs/concepts/what-is-tailscale

## Límites y pendientes

- Otra PC Windows 11 física, permisos/firewall distintos, CPU ARM y equipos corporativos. Los perfiles Android y el instalador transportable se prueban por separado; no sustituyen esa instalación física. Windows actual es x64.
- No se apagó, reinició, bloqueó ni suspendió Windows durante las pruebas. Confirmación, cuenta atrás y cancelación están probadas con simulación. No existe encendido remoto ni desbloqueo de Windows.
- No se inició ninguna partida, compra, envío de mensaje, grabación ni sesión nueva. Abrir un lanzador puede mostrar o iniciar su propia actualización. Algunas ventanas tardaron más de los 18 segundos del barrido; la apertura con diseño espera hasta 30 segundos, sin reenviar la orden por tardanza.
- Los controles multimedia genéricos dependen del reproductor elegido por Windows. No se valida el cambio real de canciones de todos los reproductores ni una sesión musical completa de TIDAL. El informe de AIMP separa lo que se comprobó.
- Ventanas fijas, splash, múltiples ventanas, juegos a pantalla completa exclusiva y lanzadores compartidos pueden requerir seleccionar en Mi PC o ajustar la propia app. No se convierten esos casos en aprobados.
- No se desconectaron monitores ni se cambió su escala. Movimiento real en los dos existentes y ausencia/ambigüedad con datos controlados.
- No se reinició Windows para comprobar inicio automático ni se dejó Android horas bajo ahorro de batería. El sistema puede detenerlo; al abrirlo intenta reconectar.
- Se recuperó una terminación inesperada real. No se simuló un bloqueo prolongado de Windows ni un fallo simultáneo del supervisor y receptor. No existe recuperación universal frente a disco defectuoso, sistema congelado o red caída.
- Ventanas que no aceptaron cierre normal o de identidad ambigua se conservaron. Puede quedar un lanzador o diálogo de actualización/prueba; no se forzó el cierre de apps ajenas.

## Evidencias y continuidad

`artifacts/beta-tests.txt`, `beta-android-tests.txt`, `beta-ui-tests.txt`, `beta-recovery-tests.json`, `beta-support-export-test.json`, `windows-live-tests.json`, `catalog-beta-*.json` y `catalog-beta-summary.md`. Se conservan resultados iniciales y repeticiones tras correcciones. Los paquetes compartibles no incluyen claves, tokens ni datos de vinculación. Los inventarios detallados son informes locales y pueden contener rutas del usuario.

**Escritorio/Eddy Deck** conserva guía, documentación, informes y versiones de código/APK/Windows. Cada entrega se publica con `scripts/publish_desktop.py` después de compilar Windows, compilar Android y empaquetar. La regla está en `AGENTS.md` para futuras modificaciones.
