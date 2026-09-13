# Cómo está programado Eddy Deck 2.2

Documento técnico de la base 2.2, actualizado para 2.2.3-beta.5. Para usar la aplicación, consulta MANUAL-USUARIO.html. FIABILIDAD-BETA4.md detalla las correcciones recientes.

## Componentes y flujo de una orden

Android es una aplicación Java con interfaz HTML/CSS/JavaScript incluida en el APK. WebView solo carga recursos internos de `app.eddydeck.local`. No tiene permiso para convertir cualquier sitio web en un control de la computadora. La interfaz llama a un puente limitado de Java; los tokens de control permanecen fuera de JavaScript.

Windows ejecuta un receptor Python empaquetado con PyInstaller, una ventana Tk y un icono de bandeja. No requiere un Python instalado aparte. El receptor, su supervisor y el comprobador no dependen de Codex ni de una API de IA.

La interfaz valida lo básico y asigna un identificador de solicitud. Android selecciona exclusivamente las direcciones privadas asociadas a la PC elegida y verifica su certificado. Windows autentica el token, valida la operación y guarda un recibo antes de ejecutarla. Las aperturas, movimientos, cierres y rutinas pasan por una cola serial; música y cancelación de energía tienen caminos independientes.

El registro SQLite distingue una orden recibida de una orden cuyo resultado se desconoce. Un reinicio no vuelve a ejecutar automáticamente trabajo interrumpido. No es posible convertir las acciones de Windows y el registro local en una transacción atómica: si ocurre un corte en el instante de actuar, el usuario debe revisar el resultado.

La interfaz conserva el identificador cuando una respuesta 409 indica trabajo en curso o una respuesta 500 deja incertidumbre; consulta el recibo antes de descartarlo. Una respuesta atrasada solo puede quitar su propio identificador, nunca el de una pulsación posterior. El historial duradero de recibos no se poda para evitar que una orden antigua vuelva a ser ejecutable; su tamaño en disco crece con el uso.

## Mapa de código

| Archivo o directorio | Responsabilidad |
| --- | --- |
| `companion/core.py` | API, PIN, autenticación, validación, perfil, referencias de apps, admisión de trabajos |
| `companion/jobs.py` | SQLite, recibos, cola limitada, pausa, cancelación, resultados y recuperación tras interrupción |
| `companion/windows.py` | Inventario, aperturas, adaptadores multimedia y energía |
| `companion/layout.py` | Monitores actuales, identificación de HWND/proceso/creación, protección y control de ventanas |
| `companion/diagnostics.py` | Diagnóstico local, redacción de datos sensibles y rotación |
| `companion/supervisor.py` | Reinicio del hijo propio, comprobación de salud y límite de fallos |
| `companion/awake.py` | Solicitud de mantener Windows despierto y liberación desde su hilo propietario |
| `companion/ownership.py` | Propiedad exclusiva por carpeta antes de recuperar datos o tareas |
| `companion/installer.py` | Copia verificada, sustitución por directorios, restauración explícita del perfil |
| `companion/integrity.py` | Manifiesto firmado, hashes, copia de reparación y comprobador externo |
| `installer/Compatibility.cs` | Comprobador .NET independiente, compatibilidad, instalación y recuperación |
| `ui/app.js`, `extended.js`, `beta2.js` | Interfaz, rutinas, recibos locales, controles de ventana y ayuda |
| `ui/manual.js` | Manual incorporado, generado desde el Markdown |
| `Connections.java` | Almacén AES-GCM, selección de PC, rutas, TLS y redescubrimiento verificado |
| `WorkLanes.java` | Ejecución separada de red, operaciones locales y archivos, con colas acotadas |
| `ExportFiles.java` | Copias temporales privadas para exportaciones grandes y recreación de Activity |
| `ConnectionService.java` | Servicio con notificación, latidos y avisos de cambio de red |
| `SupportReports.java` | Eventos de soporte sin secretos, cuerpos de API ni URLs |
| `tests/` | Pruebas de lógica, HTTP/TLS, interfaz, Windows, Android y ensayos prolongados |

## Estado y límites operativos

El perfil usa esquema 2. Guarda hasta 200 botones y 50 rutinas; cada rutina admite 24 pasos y cada espera hasta 30 segundos. Se comprueba un límite de cinco minutos por ejecución. La cola admite 20 tareas pendientes. Pausar no detiene el trabajo actual: retiene los siguientes trabajos.

La deduplicación de trabajos incluye dispositivo, nombre, pasos y política de errores. La cola usa una copia de los pasos al recibirlos; editar la rutina después no cambia el trabajo enviado. Antes de abrir o mover se vuelve a comprobar que existan la aplicación y el monitor. Una pantalla ausente solo se sustituye por la principal si el usuario habilitó esa alternativa.

El servidor limita las solicitudes ordinarias a 128 KiB; las importaciones autenticadas admiten hasta 4 MiB de transporte. El perfil serializado tiene un límite adicional de 1.5 millones de bytes para evitar producir copias que luego no puedan recuperarse. El tamaño del transporte no sustituye las validaciones de cantidad, tipo, URL o comandos permitidos.

Cada dispositivo dispone de un límite de 180 solicitudes registradas por minuto. El receptor limita las conexiones simultáneas y los tiempos de lectura. Una desconexión al rechazar un cuerpo inválido no constituye aceptación de la orden. Los recibos no se purgan automáticamente para evitar que una orden antigua vuelva a parecer nueva; su base puede crecer con el uso prolongado.

Android dispone de cuatro tareas de red y hasta 16 pendientes, y otra vía para tareas locales con una tarea activa y ocho pendientes. Una tarea que espera más de ocho segundos en el celular se rechaza antes de enviarse. La reparación de la propia Activity puede solicitarse directamente aunque la red esté ocupada.

La escritura del archivo elegido tiene una vía adicional, con una tarea activa y cuatro pendientes. Al reconstruir la Activity se rechazan nuevas escrituras de la instancia anterior, pero se deja terminar las que ya fueron aceptadas. Un fallo del proveedor de archivos se registra y se informa; no equivale a una exportación completada. La PC de una importación se captura antes de leer su archivo.

Las exportaciones de panel e informe usan archivos temporales privados diferentes. En el estado de Activity solo se conservan referencias pequeñas. Tras guardar o cancelar se eliminan esos temporales; los abandonados se limpian después de un día. No se guarda el JSON completo en el Bundle de Android. [Guía oficial de estado y Bundle](https://developer.android.com/guide/components/activities/parcelables-and-bundles).

## Identificación y seguridad de ventanas

Una ventana se reconoce por HWND, PID, creación del proceso, clase y asociación de aplicación. La identidad se vuelve a comprobar antes de actuar. Se usan asociaciones de ejecutable, AUMID y adaptadores específicos de lanzadores; no se decide por una similitud de título.

Los destinos fijos de pantalla usan `MONITORINFOEX.szDevice`, con el prefijo `display:`. No se implementó una identidad física persistente por EDID ni una migración automática de esos destinos entre PCs o docks. Se debe revisar la selección después de cambiar la configuración física. [Información de monitor de Windows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-monitorinfoexw).

La asociación UWP retiene el proceso observado cuando Windows separa temporalmente el hijo al minimizar, siempre que siga siendo el mismo proceso. La lista excluye superficies sensibles y el escritorio de Explorer. Abrir una app ya abierta conserva su ventana; si es única y minimizada, se restaura sin recalcular su tamaño. Las URLs sí se envían al navegador.

Cerrar normalmente envía WM_CLOSE y observa si la ventana desaparece. Si sigue abierta se informa que necesita atención; no se responde a cuadros de guardar. [Cierre de ventanas en Windows](https://learn.microsoft.com/en-us/windows/win32/learnwin32/closing-the-window).

Finalizar requiere una confirmación de veinte segundos vinculada a la PC, dispositivo y ventana. No sirve como confirmación de energía. Se vuelve a comprobar al ejecutar, incluyendo expiración, proceso crítico, PID y fecha de creación mediante un handle retenido. No se finalizan árboles de procesos, Windows, Explorer, Eddy Deck ni hosts protegidos; tampoco se elevan permisos.

La protección de una ventana vive en memoria. No es un permiso de Windows ni una congelación del programa. Se pierde al desaparecer la ventana o reiniciar el receptor. No cancela una operación que ya alcanzó su acción del sistema.

## Compatibilidad y recuperación

El comprobador C# utiliza .NET Framework disponible en Windows 11 y funciona sin el Python de Eddy Deck. Revisa compilación de Windows, arquitectura de 64 bits, paquete, firma, archivos y espacio para preparar la actualización. El paquete contiene el runtime Python y bibliotecas, además de las herramientas USB y sus avisos.

Windows ARM puede ejecutar aplicaciones x64 mediante emulación, pero el paquete y sus dependencias requieren validación en un equipo ARM real. La entrega no tiene una compilación nativa ARM. [Emulación en Windows ARM](https://learn.microsoft.com/en-us/windows/arm/apps-on-arm-x86-emulation).

El manifiesto enumera cada archivo con tamaño y SHA-256. Se firma con RSA de 3072 bits y PKCS#1 v1.5/SHA-256. La clave pública se incluye en Python y C#; la privada permanece en el proyecto original. Se rechazan firmas incorrectas, rutas fuera de la carpeta, enlaces y archivos adicionales. Esto presupone un comprobador obtenido de una copia confiable; no reemplaza Authenticode ni protege una PC cuyo administrador o programa ya está comprometido.

La actualización prepara y verifica otro directorio antes de sustituir el actual. Conserva una carpeta de versión anterior. Los datos permanecen en `%LOCALAPPDATA%/EddyDeck`; los binarios están en `%LOCALAPPDATA%/Programs/EddyDeck`.

En `recovery` se conserva un ZIP verificado; en `Rescue` vive una copia del comprobador fuera de los binarios principales. La reparación detiene solo los procesos de Eddy Deck que coinciden con el ejecutable instalado, empezando por el supervisor. Después instala y abre la app. Una reparación de archivos no intenta arreglar silenciosamente un perfil, certificado o almacén de credenciales dañado.

La restauración explícita de un JSON de botones y rutinas se valida antes de detener el receptor. El archivo anterior se conserva aunque sea ilegible. No se sustituyen dispositivos ni certificados. Recuperar una conexión cifrada dañada requiere el procedimiento de vinculación; no se copian claves de otra PC o teléfono.

## Actualizaciones y respaldo privado

Drive almacena entregas, instaladores, código, documentación y evidencias. No se incrustan credenciales de Google ni un permiso global de Drive en el APK o comprobador. El botón abre la carpeta privada en el navegador; el usuario descarga la versión y elige la carpeta extraída. El comprobador valida esa copia. No hay un actualizador automático que consulte Drive sin iniciar sesión.

La entrega tiene un ZIP independiente de Windows y un paquete completo. El APK lleva exactamente ese Windows; por eso se compila Windows antes de Android. `package_release.py` verifica que los documentos sigan coincidiendo con la compilación. `publish_desktop.py` conserva versiones anteriores y comprueba hashes al copiar.

Los secretos de compilación quedan fuera: `private/android-signing.p12`, su contraseña y `private/release-signing.pem`. Las claves de Android Keystore no son transferibles al teléfono nuevo: se instala el APK y se vincula de nuevo. El perfil de la PC se conserva.

Tailscale es una dependencia externa para acceso por internet. Sus claves de dispositivo pueden vencer y requerir autenticación nuevamente; no se debe forzar esa renovación a distancia si no hay otra forma de recuperar acceso. USB y red local son rutas independientes. [Caducidad de claves de Tailscale](https://tailscale.com/docs/features/access-control/key-expiry).

## Cobertura y pendientes

VALIDACION.md y los JSON de `Informes` distinguen hardware real, adaptadores simulados, observaciones parciales y casos pendientes. El barrido de aperturas de la beta 1 sigue siendo histórico; una prueba de crear botones no se presenta como prueba de uso completo de una aplicación. No se ejecutan compras, publicaciones, grabaciones, borrados de documentos ni energía real para inflar la cobertura.
