# Eddy Deck

**Código público basado en 2.2.8-beta.10.** Incluye Windows, Android, interfaz, pruebas y manual. Los destinos personales de respaldo y los identificadores de dispositivos se sustituyeron por ejemplos. Esta copia no es idéntica a los instaladores privados; estos no se publican aquí. Consulta [PUBLICACION.md](docs/PUBLICACION.md) antes de compilar o ejecutar pruebas en dispositivos.

## Versión base: 2.2.8 · Beta 10

Tu PC desde Android: aplicaciones, música, ventanas y rutinas. Windows y Android ejecutan el programa por sí mismos, sin IA ni suscripción a Codex. USB y Wi-Fi funcionan sin cuentas. Para controlar desde datos móviles, esta versión usa Tailscale; requiere su aplicación y una cuenta en ambos equipos.

## Manual y novedades de esta beta

Beta 10 corrige el bloqueo de rutinas al maximizar Roblox: su ventana no declara los botones habituales, pero acepta maximizarse. Ahora se comprueba el resultado real. Al abrir una aplicación puedes elegir **Traer al frente** (predeterminado, también para botones/rutinas anteriores) o **Dejar que Windows decida**. La opción se guarda en botones y pasos de apertura; mover y controlar música conservan su comportamiento. Si eliges **Minimizada**, tiene prioridad. Consulta [aperturas y primer plano](docs/APERTURAS-BETA10.md).


Beta 9 corrige la identidad distinta entre arranques desde Codex y desde Windows: todos usan ahora `%USERPROFILE%\.eddydeck`. Conserva certificados, vinculación, botones y rutinas; las carpetas anteriores permanecen como respaldo. Mejora la búsqueda de la misma PC tras cambios de red y evita reenviar órdenes a ciegas. Consulta [la reconexión y sus límites](docs/RECONEXION-BETA9.md).

Beta 8 pule la interfaz con tonos claros, acento verde, navegación flotante y formularios más legibles. Los menús de edición tienen opciones propias, búsqueda en listas largas y soporte de teclado y Atrás. Las rutinas conservan sus valores y orden. Consulta [el diseño y sus pruebas](docs/DISENO-BETA8.md). No cambia el protocolo ni los motores de control de aplicaciones.

Windows evita la suspensión automática mientras Eddy Deck está ejecutándose, incluso junto al reloj. Al salir libera esa solicitud; no modifica el plan de energía ni impide apagar el monitor. Android mantiene la pantalla encendida solamente mientras Eddy Deck está en primer plano. Bloquear manualmente, suspender desde Windows, cerrar la tapa, políticas del sistema o batería agotada pueden interrumpir la conexión; no hay despertar remoto.

Lee [el manual de usuario](docs/MANUAL-USUARIO.html) para las instrucciones completas, ejemplos y solución de problemas. La versión [Markdown](docs/MANUAL-USUARIO.md) también se conserva. [VALIDACION.md](docs/VALIDACION.md) es el informe técnico de pruebas y pendientes.

Beta 7 corrige la selección de música entre aplicaciones, la pausa inmediata tras cambiar pista en TIDAL y pérdidas de edición en rutinas. Media Player y otras sesiones que Windows expone aparecen como destinos explícitos. Consulta la [matriz de funciones y pruebas](docs/MATRIZ-FUNCIONES-BETA7.md) y [los resultados y límites](docs/VALIDACION.md).

Beta 5 corrigió la reparación cuando falla el registro de cancelaciones y las respuestas atrasadas al cambiar de PC. Primero cancela y registra las tareas; después inicia la reparación. Ante un disco que no permite guardar, la cola se detiene y avisa. Consulta [los casos de fallo combinados](docs/FIABILIDAD-BETA5.md).

La beta 4 corrigió los tiempos de confirmación cuando cambia la hora, los refrescos que coinciden con un guardado y la apertura de dos receptores sobre los mismos datos. Explica los fallos de inicio y libera los recursos incluso si falla el registro al cerrar. También impide que un editor antiguo vuelva a crear una rutina eliminada. El volumen de Windows está en Inicio; Bloquear está en Mi PC → Energía. Consulta [los cambios de fiabilidad](docs/FIABILIDAD-BETA4.md).

Esta beta conserva los controles para ventanas existentes (minimizar, restaurar, proteger, cerrar y finalizar con confirmación), pausa de tareas siguientes, asociación prudente de apps actualizadas o importadas, comprobación firmada de archivos y reparación independiente de la aplicación Windows. Android reacciona a cambios de red, limita órdenes pendientes y conserva una copia del manual e informes.

También recupera explícitamente una copia de botones cuando el perfil está dañado, distingue versiones incompatibles y conserva los recibos correctos ante respuestas atrasadas. Consulta [la arquitectura y el mapa de código](docs/ARQUITECTURA-BETA2.md) y [la matriz de compatibilidad](docs/COMPATIBILIDAD-Y-SEGURIDAD.md).

El [entorno de compilación](docs/ENTORNO-COMPILACION.md) registra herramientas, dependencias y cuidados para futuras actualizaciones.

En esta copia pública, el [botón de Drive](https://drive.google.com/drive/my-drive) abre la página general de tu propio Drive. Configura tu carpeta antes de distribuir tu compilación. Se abre en el navegador para descargar con tu cuenta; después el comprobador verifica el paquete extraído. No se configuró una actualización silenciosa desde Drive.

## Uso diario

1. Abre **Eddy Deck** en Windows. Cerrar su ventana lo deja junto al reloj; **Salir** detiene el receptor. En esta PC quedó activado **Iniciar Eddy Deck al entrar a Windows**. Puedes desactivarlo desde su ventana o el panel local.
2. Abre **Eddy Deck** en Android. Recuerda la computadora elegida y reconecta al abrirse. **Mis PCs** permite cambiar entre computadoras sin borrar las otras.
3. En **Biblioteca** busca una app y pulsa **+**. Detecta Inicio, accesos directos y juegos Steam/Epic. Se sincroniza al iniciar, cada cinco minutos y con **Sincronizar**. Puedes agregar un `.exe` portable desde Windows.
4. Mantén pulsado el botón de abrir o toca **…** para guardar nombre, color, URL, pantalla y tamaño. **Preguntarme al abrir** solicita la pantalla cuando abres esa app. Los controles de música no preguntan por monitores.

Windows debe estar encendido, despierto, con tu sesión iniciada y Eddy Deck ejecutándose. El inicio automático ocurre al entrar a Windows, no antes del inicio de sesión. Esta versión no enciende ni despierta la PC a distancia.

## Conexiones

| Método | Preparación |
| --- | --- |
| USB | Autoriza la depuración USB en Android y pulsa **USB** en Windows. Al reconectar el cable, vuelve a pulsarlo. Incluye las herramientas oficiales ADB. |
| Wi-Fi / red local | Ambos equipos en la misma red. Para la primera vinculación busca la PC desde Android o escribe su IP; después se intenta redescubrirla automáticamente. Compara la huella y usa su código de ocho dígitos. |
| Datos móviles / otra red | Instala Tailscale en ambos, inicia sesión con la misma cuenta y activa su VPN en Android. Vincula Eddy Deck y verifica/guarda la IP `100.x.x.x` en **Ajustes → Internet privado**. |

Android aprende las direcciones actuales también con las comprobaciones en segundo plano. Antes de una orden comprueba una ruta hacia la identidad ya vinculada; la orden se envía una sola vez. Si cambia la IP local, redescubre la misma PC en Wi-Fi y verifica su certificado. Conserva la IP privada de Tailscale aunque su adaptador tarde en aparecer. El acceso remoto requiere Tailscale conectado en ambos equipos; en Android configura **VPN siempre activada** (sin bloquear conexiones ajenas a la VPN). No necesitas otro código por reiniciar o cambiar de Wi-Fi.

Si el firewall bloquea Eddy Deck, **Activar Wi-Fi** permite solo su ejecutable, TCP 47990 y UDP 47991, desde la subred local. **Activar internet** permite TCP 47990 desde `100.64.0.0/10`. Windows puede pedir permiso de administrador. No abras puertos en el router ni desactives el firewall. La conexión privada pudo verificarse aquí sin agregar esas reglas opcionales.

Tailscale es un componente externo, independiente de la IA. Su disponibilidad, cuenta, VPN y restricciones de red afectan el acceso por internet. USB y Wi-Fi siguen siendo alternativas. No se configuró un nodo de salida ni se aceptaron rutas o DNS de Tailscale en esta PC: se usa su IP privada.

## Ventanas y pantallas

- **Destino:** como la dejé, izquierda, derecha, vertical, principal o una pantalla concreta. Izquierda/derecha se determinan por la disposición que reporta Windows. Con varias verticales, elige una concreta.
- **Tamaño:** conservar, modo ventana, maximizada, minimizada o mitad izquierda/derecha de esa pantalla.
- **Si falta una pantalla:** detener y avisar, o usar la principal. Solo se utiliza esa alternativa cuando la elegiste.
- **Mi PC → Ventanas abiertas → Controlar:** selecciona una ventana exacta para mover, minimizar, restaurar o cerrar normalmente. La protección impide esas órdenes durante la vida de la ventana y del receptor. La finalización requiere una confirmación reciente y excluye procesos de Windows y hosts protegidos. Se vuelve a identificar antes de actuar; una ventana cerrada no se sustituye por otra al azar.

**Maximizada** ocupa el área de trabajo de Windows. La pantalla completa exclusiva de juegos/reproductores se configura dentro de esas apps. Algunas imponen su posición o un tamaño mínimo. Eddy Deck informa si no aceptan el diseño.

Una apertura con diseño espera hasta 30 segundos por una ventana identificable. Hay adaptadores para ejecutables normales, apps empaquetadas y algunos lanzadores (Opera, Roblox, Discord y TIDAL). Si hay un lanzador no reconocido o varias ventanas posibles, se avisa: selecciona la ventana en Mi PC. No se elige por coincidencias aproximadas de título.

## Rutinas

En **Rutinas → Crear rutina**, escribe un nombre y agrega pasos:

1. Abrir una app, opcionalmente con URL, monitor y tamaño.
2. Mover una app que ya tiene una ventana abierta.
3. Controlar música: reproducir/pausar, anterior, siguiente, detener o silencio.
4. Esperar entre 0 y 30 segundos.

Edita, elimina o sube pasos. Elige **detener si falla** o **registrar el error y continuar**. Se admiten 24 pasos y se comprueba un límite de cinco minutos por ejecución. No se admiten comandos arbitrarios ni acciones de energía dentro de las rutinas.

Ejemplo, si ambas están instaladas: **abrir Roblox → derecha → maximizada**, seguido de **abrir TIDAL → vertical → modo ventana**. Las URLs se editan en cada paso de navegador. No necesitas IA para cambiar estas combinaciones.

Aperturas, movimientos, cierres y rutinas usan una sola cola. **Pausar siguientes tareas** deja terminar la tarea o rutina actual y retiene las siguientes hasta reanudar. La música responde por separado. **Cancelar** detiene pasos pendientes y conserva lo ya abierto. Revocar un celular cancela sus pasos pendientes. **Cola y resultados** muestra los resultados y errores de cada paso. Una aplicación que pide actualización, cuenta o permiso puede necesitar intervención local; no se vuelve a abrir automáticamente solo por tardar.

## Música y energía

Automático consulta TIDAL, AIMP y las sesiones multimedia que publica Windows. Si hay más de una reproduciendo, pide elegir en Música. TIDAL y AIMP tienen control directo; Media Player y otras sesiones tienen destinos separados y capacidades consultadas. Las teclas de Windows quedan como opción explícita sin confirmación. No se muestran carátula ni título de canción. El silencio general afecta todo Windows; AIMP tiene volumen propio.

Bloquear, suspender, reiniciar y apagar requieren confirmación reciente y esperan 15 segundos. Puedes cancelar desde Android o la bandeja de Windows. Confirmar energía cancela pasos pendientes de rutinas y bloquea nuevas aperturas durante la cuenta atrás. No se fuerza el cierre de documentos; Windows puede pedir guardar o impedir el apagado.

## Segundo plano en Android

Activa **Ajustes → Conexión en segundo plano** y permite notificaciones. Muestra una notificación permanente con el estado y un botón de desconexión. Reacciona a cambios de red y comprueba la conexión cada 25 segundos y conserva la preferencia. Al reabrir la app recupera la PC seleccionada.

El servicio solicita al sistema reinicio normal si termina y puede regresar después de reiniciar el teléfono. Android/Samsung conservan el control: ahorro de batería, suspensión profunda, forzar detención, cerrar la VPN o reiniciar antes de desbloquear pueden impedirlo. Abre Eddy Deck y comprueba Tailscale para recuperar la conexión. Puedes ajustar **Información de la app → Batería**. No se desactivan protecciones silenciosamente.

## Otra computadora

En Android abre **Mis PCs → Llevar instalador → Guardar instalador Windows**. El APK contiene un ZIP completo de Windows. Guárdalo y pásalo por USB, Bluetooth o la opción Compartir del teléfono.

En la otra PC con Windows 11 de 64 bits:

1. Extrae todo el ZIP; conserva `_internal` y `usb`.
2. Ejecuta **Instalar.cmd**. Abre el comprobador independiente: revisa Windows, arquitectura, firma y archivos; al instalar también revisa espacio libre. Instala por usuario y crea accesos directos.
3. Abre Eddy Deck, permite la red si Windows lo solicita y usa **Agregar PC** en Android con su código y huella.
4. Su catálogo, botones y rutinas se guardan en esa computadora.

Bluetooth transfiere el instalador; el control posterior usa Wi-Fi, USB o Tailscale. La búsqueda Wi-Fi requiere el receptor instalado y abierto. No existe instalación silenciosa sobre una PC desconocida. En Windows ARM, este paquete x64 depende de la emulación; no se ha probado en ARM. No se dispone de una segunda PC física para verificar todo ese recorrido.

Cada PC genera identidad propia. **No copies `server.key` ni `devices.json` a otra PC que deba coexistir con la actual.** Vincúlala por separado. Puedes importar botones/rutinas, pero revisa sus aplicaciones y pantallas.

## Datos y recuperación

### Reparación e informes

Al final de **Inicio** y en **Ajustes** están **Reparar app del celular**, **Reiniciar conexión de Windows** y **Guardar informe**.

- Reparar el celular reconstruye la interfaz y reinicia su servicio de conexión si lo tenías activado. Conserva los vínculos cifrados y los identificadores de órdenes pendientes; no vuelve a ejecutar automáticamente una orden incierta.
- Reparar el receptor guarda un informe, cancela las rutinas pendientes y la cuenta atrás de energía y reinicia únicamente los procesos de Eddy Deck en Windows. Las otras aplicaciones permanecen abiertas. Requiere conexión y confirmación. Se limita a una reparación por minuto.
- El supervisor de Windows intenta recuperar el receptor si su proceso termina inesperadamente o deja de responder. Tiene espera entre intentos y se detiene después de cinco fallos en quince minutos. **Salir** desde la bandeja es una salida intencional y detiene ambos procesos. No fuerza a reabrir una app que decidiste cerrar.
- Si el receptor está desconectado, el celular no puede enviarle una reparación. Usa la reparación del celular, comprueba Tailscale y espera al supervisor. Si sigue fallando, abre Eddy Deck en Windows. Si el supervisor no responde, sal desde la bandeja y vuelve a abrirlo.
- **Guardar informe** exporta diagnóstico del celular y de la PC si esta responde. Incluye versiones, cantidades, estado de la cola, errores y acciones recientes; no incluye tokens, PIN, URLs, títulos de ventanas ni claves. Si se daña el almacén de vínculos, todavía puedes exportar un diagnóstico del celular; no se borra ese almacén automáticamente.
- Windows guarda `audit.jsonl` y una copia rotada, hasta 100 informes en `reports/`, y conserva los recibos duraderos en SQLite. Android conserva las últimas 100 entradas de soporte. Los latidos normales no llenan el historial de acciones. Los informes son archivos locales; no se envían a nadie automáticamente.

El panel del navegador de Windows puede necesitar abrirse otra vez desde la bandeja después de reparar el receptor, porque renueva su permiso local. El celular conserva su vínculo y reconecta por sí mismo.

### Reparación completa del programa Windows

**Comprobar archivos de Windows** verifica la firma RSA/SHA-256 y cada archivo. **Reparar archivos de Eddy Deck** utiliza la copia local firmada en `recovery` y el comprobador independiente en `Rescue`, cancela tareas pendientes y reinstala solo Eddy Deck. Conserva sus datos y las otras aplicaciones. Si no hay conexión, abre el acceso directo **Eddy Deck - Reparar** en Windows. La herramienta incluye un botón para abrir tu respaldo privado de Drive y elegir otra copia extraída. No repara Windows ni los archivos de aplicaciones ajenas.

### Particularidades de las aplicaciones

El catálogo verifica la instalación de los juegos de Steam mediante sus manifiestos locales y vincula sus ventanas con esa carpeta concreta. Reconoce lanzadores de Blender, CapCut, Git GUI y Steam, además de los adaptadores anteriores. Excluye accesos obsoletos o herramientas del sistema que no corresponden a aplicaciones normales. Un lanzador compartido entre varios productos no prueba qué producto tiene una ventana: para esos casos abre normalmente y selecciona la ventana exacta en **Mi PC**. Consulta [el resultado por aplicación](docs/CATALOGO-PRUEBAS.md).

**Modo ventana** solicita un tamaño cómodo, respetando el tamaño fijo, las proporciones y los mínimos de la aplicación. **Maximizada** y las mitades de pantalla pueden no estar disponibles en reproductores con skins o juegos. La interfaz de conexión de Windows tiene desplazamiento vertical para pantallas pequeñas.

### Entregas en tu escritorio

La carpeta **Escritorio → Eddy Deck** reúne `MANUAL-USUARIO.html`, `GUIA-DE-USO.md`, `PRUEBAS-Y-LIMITES.md`, `Informes` y `Versiones`. Cada versión incluye código fuente, APK e instaladores. Para actualizarla tras compilar y empaquetar ejecuta `scripts/publish_desktop.py`; comprueba las copias y conserva las versiones anteriores. El instalador que lleva Android se actualiza compilando Windows primero.

Programa: `%LOCALAPPDATA%\Programs\EddyDeck`. Datos actuales: `%USERPROFILE%\.eddydeck`.

| Archivo | Uso |
| --- | --- |
| `deck.json` | Botones y rutinas, esquema 2 |
| `deck-before-v2.json` | Copia antes de migrar desde la versión 1 |
| `manual-apps.json` | Apps portables |
| `devices.json` | Identificadores y hashes de acceso; no tokens en claro |
| `server.crt`, `server.key` | Identidad TLS de esta PC; la llave es privada |
| `operations.sqlite3` | Recibos de órdenes y resultados de trabajos |
| `eddydeck.log` | Diagnóstico con rotación |

Android cifra las conexiones con AES-GCM y una clave de Android Keystore. Cada PC tiene token, huella y direcciones independientes. Los tokens no se exponen a JavaScript ni se respaldan automáticamente en la nube. Windows exige TLS con huella exacta, código de uso único y token revocable. El panel HTTP solo escucha en el propio Windows; su token local no autoriza peticiones por red.

Un identificador recibido no se ejecuta de nuevo, incluso tras reiniciar. Si se interrumpe una operación, se muestra **interrumpida** o resultado incierto. **No se reanuda automáticamente**: las acciones de Windows no constituyen transacciones. Revisa el resultado antes de enviar otra orden.

La actualización de Windows prepara y verifica una carpeta nueva antes de sustituir la anterior. Conserva `EddyDeck-previous-…` junto al programa para recuperación. La configuración vive fuera de esa carpeta. Si un archivo de configuración está dañado, se conserva y se informa; no se borra para ocultarlo.

**Guardar una copia** exporta botones y rutinas sin claves. **Restaurar** conserva antes el perfil anterior. Si borras los datos de Android o pierde la clave de Keystore, vuelve a vincularlo y revoca el vínculo anterior desde Windows.

## Mantenerlo sin Codex

Código normal en Python, Java y HTML/CSS/JavaScript, con licencia MIT para el código propio. Conserva las licencias de componentes externos incluidas con Windows.

```text
python -m venv .build\venv
.build\venv\Scripts\python.exe -m pip install -r requirements.txt
.build\venv\Scripts\python.exe scripts\setup_toolchain.py
.build\venv\Scripts\python.exe -m unittest discover -s tests -v
.build\venv\Scripts\python.exe scripts\build_windows.py
.build\venv\Scripts\python.exe scripts\build_android.py
.build\venv\Scripts\python.exe scripts\package_release.py
```

Compila Windows antes de Android: el APK lleva ese instalador. Respalda privadamente `private/android-signing.p12`, `private/signing-password.txt` y `private/release-signing.pem` del proyecto original. Las dos primeras permiten actualizar Android con su firma; la tercera firma los paquetes Windows. Deben conservarse de forma privada para futuras versiones. Nunca se incluyen en el ZIP para compartir.

| Código | Función |
| --- | --- |
| `companion/windows.py` | Catálogo, apertura, música y energía |
| `companion/layout.py` | Pantallas, identificación, protección y control de ventanas |
| `companion/integrity.py`, `installer/Compatibility.cs` | Integridad firmada, comprobador y reparación independiente |
| `companion/jobs.py` | Registro duradero y cola cancelable |
| `companion/core.py` | API, autenticación, perfiles y validación |
| `companion/desktop.py`, `installer.py` | Bandeja, QR, inicio e instalación |
| `ui/app.js`, `ui/extended.js`, `ui/beta2.js`, `ui/manual.js` | Interfaz base y controles de versión 2 |
| `android/src/com/eddy/deck/` | App, almacenamiento cifrado y servicio |
| `tests/` | Pruebas unitarias, interfaz e instrumentación Android |

Para pruebas visuales v2 instala Playwright para Node, ejecuta `scripts/test_server.py` con Python del entorno y después `node tests/ui-v2.cjs`. Utiliza `.build/v2-test-data` y puertos 48089/48090, separados del programa normal, en simulación. `tests/windows_live.py` abre una Calculadora nueva para comprobar movimientos reales y luego cierra solo esa ventana; omite la prueba si Calculadora ya está abierta. `scripts/build_android_tests.py` genera un APK separado de instrumentación, firmado igual, que usa preferencias aisladas.

Al publicar actualizaciones cambia la versión en `companion/core.py` y `versionCode`/`versionName` de Android. Instala el APK con la misma firma. En Windows sal de Eddy Deck antes de ejecutar Instalar.cmd.

## Referencias y límites

- [Tailscale en Windows](https://tailscale.com/docs/install/windows) y [Android](https://tailscale.com/docs/install/android).
- [Servicio Android para dispositivos conectados](https://developer.android.com/develop/background-work/services/fgs/service-types#connected-device).
- [ADB](https://developer.android.com/tools/adb) y [firma de APK](https://developer.android.com/tools/apksigner).
- [Estado y posición de ventanas de Windows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowplacement).
- [SDK de AIMP](https://aimp.ru/?cat=sdk&do=download&os=windows).

Consulta **docs/VALIDACION.md** para distinguir pruebas realizadas y pendientes. No existe una garantía absoluta frente a fallos de Windows, Android, otras aplicaciones o la red.
