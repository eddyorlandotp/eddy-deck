# Disponibilidad de los equipos · 2.2.1-beta.3

Windows usa un hilo dedicado con SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED). El mismo hilo libera ES_CONTINUOUS al terminar. No solicita ES_DISPLAY_REQUIRED ni AWAYMODE, no modifica el plan de energía y no pretende impedir una suspensión manual. Un fallo de la API queda visible en Mi PC y se vuelve a intentar después de 30 segundos. Solo el arranque real del receptor adquiere esta protección; las instancias de pruebas no la activan al construir Deck.

Android activa FLAG_KEEP_SCREEN_ON en MainActivity.onResume y lo retira en onPause. El servicio de conexión no mantiene encendida la pantalla. No se usa un permiso para desactivar el bloqueo ni una modificación global del tiempo de apagado.

Las cuatro pruebas nuevas comprueban adquisición/liberación en el mismo hilo, reintento después de un error, inicio/cierre repetidos y cierre antes de iniciar. Las evidencias físicas posteriores a instalar se guardan por separado en Informes/beta3-*. No se afirma que el programa pueda despertar un equipo suspendido ni superar políticas empresariales o batería crítica.

Referencias oficiales:
- https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
- https://developer.android.com/develop/background-work/background-tasks/awake/screen-on
