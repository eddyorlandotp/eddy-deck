# Fiabilidad y cambios de beta 4

Versión 2.2.2-beta.4. Este documento explica el diseño; VALIDACION.md separa lo observado, lo simulado y lo pendiente.

## Disponibilidad y energía

La protección de Windows pertenece a un hilo dedicado. Solicita SYSTEM_REQUIRED con CONTINUOUS y la retira desde ese mismo hilo. No solicita DISPLAY_REQUIRED ni AWAYMODE y no cambia el plan de energía. Los receptores reales, con ventana o con `--headless`, solicitan esta protección. `--dry-run` no la solicita; construir Deck para una prueba tampoco lo hace.

AwakeGuard es de un solo uso: start repetido conserva el mismo hilo; close es idempotente y definitivo. Para reiniciar se crea otro guard. Si la llamada nativa tarda, close espera hasta dos segundos; el hilo termina y libera su solicitud cuando la llamada regresa. No se mata un hilo arbitrariamente. Si falla una solicitud, se expone el tipo de error y, cuando existe, el código entero de Windows; no se deduce una causa de batería o política a partir de un error genérico.

Android usa FLAG_KEEP_SCREEN_ON en onResume y lo retira en onPause. El tiempo normal de apagado de pantalla no se aplica mientras la Activity mantiene ese flag en primer plano. Al cambiar de app vuelve el comportamiento de Android. El servicio de conexión no adquiere un bloqueo para mantener la pantalla encendida.

Referencias: [SetThreadExecutionState, Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate), [mantener la pantalla encendida, Android](https://developer.android.com/develop/background-work/background-tasks/awake/screen-on).

## Tiempos independientes de los ajustes de hora

| Control | Duración y comportamiento |
| --- | --- |
| Código de vinculación | Diez minutos; un solo uso. |
| Intentos de vinculación | Ventana de cinco minutos. |
| Confirmación de energía | Treinta segundos para confirmar. |
| Confirmación de finalización | Veinte segundos, incluyendo lo que espere después en cola. |
| Cuenta atrás de energía | Quince segundos antes de enviar la operación a Windows. |
| Órdenes por dispositivo | Hasta 180 nuevas órdenes por minuto. Repetir el mismo recibo conserva su resultado. |
| Reparación | Un minuto entre intentos. |
| Supervisor | Treinta segundos de arranque; pausa tras cinco fallos en quince minutos. |

Estos intervalos usan el reloj monotónico. Las fechas legibles y los registros históricos siguen usando fecha/hora de calendario. La respuesta pública de energía incluye segundos restantes; el panel usa performance.now para dibujar la cuenta, evitando depender de que el celular y la PC tengan la misma hora. `at` se conserva para clientes anteriores; los plazos internos y el dispositivo que confirmó no se exponen en el objeto público.

Los recibos siguen siendo duraderos. Al reiniciar, el limitador reconstruye como máximo los 180 recibos más recientes del dispositivo. Si un ajuste de hora los dejó fechados en el futuro, se cuentan de forma conservadora durante un minuto y luego vencen; no bloquean la app durante días. El índice de SQLite acelera esa consulta sin eliminar recibos. El estado de reparación sigue la misma regla de espera máxima tras una fecha futura.

La autorización del celular se vuelve a comprobar al terminar la cuenta atrás, incluso si el hilo comenzó cuando ya había vencido el plazo. Se comprueba justo antes de comprometer el envío; no se promete deshacer una operación física ya enviada.

## Un propietario por carpeta de datos

Antes de construir Deck o recuperar su Journal, el receptor adquiere un bloqueo de un byte en `receiver.lock`. Lo conserva durante su ejecución, tanto con interfaz como con `--headless` o `--data`. Windows libera ese bloqueo cuando termina el proceso, incluso si la salida fue inesperada. El archivo se conserva: no se elimina ni recrea mientras haya un receptor activo.

Esto impide que una segunda instancia convierta en interrumpidas las tareas que la primera todavía ejecuta. Además se comprueba la activación local y la salud de un receptor anterior para la transición desde versiones sin ese bloqueo. Un bloqueo por carpeta no autoriza controlar otra PC ni sustituye el certificado o el vínculo del celular.

Una identidad incompleta se conserva y se explica en el aviso de inicio; no se reemplaza automáticamente por otra identidad. Lo mismo ocurre con un JSON que no puede leerse. Cuando la inicialización falla, se cierra la cola y cualquier servidor iniciado antes de esperar una respuesta al diálogo. Un servidor cuyo hilo no llegó a iniciarse se cierra directamente, sin esperar una tarea que nunca comenzó. En modo headless el error se devuelve al proceso que lo invocó, sin abrir un diálogo.

Si falla el disco al registrar las cancelaciones del cierre, se detiene y notifica igualmente al trabajador. Los trabajos que no pudieron actualizarse quedan interrumpidos al abrir el Journal de nuevo, sin ejecución automática. Cada recurso tiene su propio intento de limpieza; el fallo de uno no omite los demás. Si no puede escribirse el registro, tampoco se garantiza un informe persistente del fallo.

Referencia: [bloqueo de archivos de msvcrt, Python](https://docs.python.org/3/library/msvcrt.html).

## Interfaz y rutinas

La firma de refresco incluye disponibilidad de energía, errores, actividad y reproducción en Inicio. Solo se marca un estado como dibujado cuando terminó el render. Mientras un diálogo conserva una edición, los cambios recibidos quedan pendientes de dibujar; al cerrarlo, el siguiente refresco los muestra.

Si un guardado termina mientras otra consulta sigue en curso, los refrescos forzados se agrupan y esperan una consulta nueva. La respuesta anterior se descarta. Esto se mantiene si aquella consulta falla o si cambia la PC seleccionada: cada consulta pertenece a la selección que la originó.

Un editor antiguo no puede guardar una rutina que se eliminó en otro panel como si fuese una rutina nueva. La copia ya encolada sigue siendo independiente de ediciones posteriores. Una validación rechazada de un botón restaura el perfil en memoria y no guarda cambios parciales.

## Revisiones y alcance

Claude Code revisa snapshots sin datos privados con Read/Grep/Glob. Codex integra y ejecuta las pruebas. Los informes conservan la base exacta y los archivos que cambiaron después; una revisión anterior no aprueba cambios posteriores automáticamente. La continuidad de los archivos permite retomar una interrupción, pero no se ha verificado un traspaso automático de escritura entre servicios.

El volumen general y Bloquear ya estaban disponibles; en esta entrega se comprueban sus rutas y comportamiento. No se presentan como nuevas funciones. El ensayo real de volumen usa Core Audio como observador independiente y restaura el nivel y silencio iniciales; no reproduce canciones.

## Entrega reproducible

La publicación en el escritorio rechaza sustituir los ZIP o el APK de una versión ya entregada por bytes diferentes. El empaquetado de evidencias exige que terminen los ensayos requeridos, que cumplan su duración y que la prueba final corresponda a los archivos actuales de companion. Los informes de resultados iniciales fallidos se conservan con su explicación; no se cambia su etiqueta a aprobado.

Una incidencia conocida de instrumentación durante la observación inicial exige una revisión explícita vinculada a la muestra y una recuperación observada. El informe original sigue conservando la incidencia. La observación posterior a la instalación debe completarse sin incidencias imprevistas.

`scripts/verify_report_privacy.py` compara informes y documentación contra los identificadores de vinculación, claves y tokens locales conocidos. Esta comprobación exacta complementa la lista permitida del paquete de código; no constituye una auditoría general de datos personales ni una certificación de seguridad.
