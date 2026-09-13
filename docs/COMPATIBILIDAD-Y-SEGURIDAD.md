# Compatibilidad, fallos y decisiones de seguridad

Matriz de Eddy Deck 2.2.3-beta.5, conservando los casos de beta 2. VALIDACION.md indica cuáles se repitieron en la entrega actual y cuáles siguen siendo evidencia histórica. Las defensas reducen fallos concretos; no garantizan invulnerabilidad ni funcionamiento perfecto con todo software.

| Situación | Respuesta prevista | Evidencia o límite |
| --- | --- | --- |
| App ya abierta | Conserva o restaura su ventana; otra apertura es opcional | Prueba real con ventanas controladas |
| Varias ventanas de una app | Exige elegir una para mover/restaurar de forma inequívoca | Pruebas de identidad y ambigüedad |
| Ventana cerrada y HWND/PID reutilizado | Rechaza identidad antigua | Verificación de proceso/creación y casos de ventana cerrada |
| Cambios pendientes en una app | Cierre normal solicita atención | Ventana de prueba rechaza WM_CLOSE |
| App protegida en Eddy Deck | Rechaza movimiento, cierre y finalización | Prueba real; protección de sesión |
| Monitor ausente o varios verticales | Detiene o usa principal según la elección guardada | Simulación; no se fingió desconexión física |
| Pantalla fija después de cambiar de PC/dock/cableado | Revisar la selección guardada | Se usa el identificador lógico de Windows, no una identidad física persistente por EDID |
| Laptop con una sola pantalla | Roles izquierda/derecha apuntan a esa pantalla | Caso simulado |
| Ningún monitor disponible | Música/apertura sin diseño permanecen utilizables; diseño se rechaza | Caso simulado; no garantiza una sesión gráfica sin hardware |
| Resoluciones o DPI distintos | Usa coordenadas físicas y consulta el área de trabajo | Dos monitores reales; otras geometrías simuladas |
| Rutinas simultáneas | Cola serial, instantánea de pasos y deduplicación | Pruebas unitarias y prolongadas |
| Reloj de PC o celular ajustado | Plazos de confirmación, limitación y supervisión monotónicos | Regresiones beta 4; fechas históricas siguen siendo informativas |
| Dos receptores con la misma carpeta | El segundo no adquiere propiedad ni recupera el Journal | Bloqueo de archivo y prueba de procesos separados |
| Disco falla durante el cierre | Detiene la cola y sigue intentando liberar recursos | Fallos inyectados; no garantiza un informe si no puede escribirse |
| Inicio incompleto o perfil ilegible | Conserva datos y explica el error después de limpiar recursos | Pruebas de arranque, diálogo y primer/segundo hilo fallido |
| Reparación o energía mientras se agregan tareas | Admisión coordinada; se cancelan pendientes | Prueba de carrera y comprobaciones de cola |
| Disco falla antes de registrar una orden | No se admite como nueva acción ejecutable | Inyección de fallos |
| Fallo de registro después de actuar | Resultado incierto o cola no saludable; no se reejecuta a ciegas | Pruebas de registro, recibos y salud |
| Actualización de una aplicación cambia su identificador | Asociación exacta y única; avisa si falta o hay ambigüedad | Casos de cambio de catálogo y reinicio |
| Copia grande de muchas rutinas | Límites coherentes, exportación por archivos temporales | Importación grande y recreación de Android |
| Red saturada o desconectada | Límites de pendientes; controles locales por otra vía | Instrumentación Android y corte real de Wi-Fi/USB |
| Cambio de PC durante un reintento | Detiene reintentos hacia la PC anterior | Instrumentación con almacén aislado |
| Respuestas fuera de orden o ejecución todavía en curso | Conserva el recibo correcto y consulta el resultado | Prueba de interfaz con transportes controlados |
| Catálogo con más de 1,500 aplicaciones | La copia contiene solo referencias utilizadas | Pruebas con 1,501 entradas y 1,400 referencias distintas |
| Broadcast falso | No basta para guardar una ruta: se requiere la identidad TLS conocida | Prueba de redescubrimiento simulado |
| Paquete incompleto o modificado | Rechazo por firma, listado y hashes | Comprobador Windows real con paquetes de prueba |
| Fallo al sustituir directorios | Conserva/restaura el directorio anterior | Inyección de bloqueo y falta de espacio |
| Binarios de Eddy Deck dañados | Comprobador externo y copia local firmada | Reparación real de un archivo propio alterado |
| Perfil de botones corrupto | Restauración explícita de copia; conserva original y vínculos | Pruebas de restauración y escritura fallida |
| Edición todavía sin guardar al reparar el celular | Puede perderse el formulario pendiente; guardar primero | No hay recuperación automática de todos los borradores |
| Ruta de extracción o instalación muy larga | Avisos de licencia con rutas cortas; usar una carpeta de extracción corta | Instalación aislada repetida tras un fallo WinError 206; no cambia la política de rutas de Windows |
| Copia de otra versión | Firma e información de versión; rechazo de retroceso de versión principal/secundaria/parche | No es un actualizador semántico universal de prereleases |
| Tailscale expirado, apagado o bloqueado | No hay control por internet hasta resolver la conexión | Requiere intervención y servicios externos |
| Datos móviles, ARM o segunda PC física | No se afirman como probados | Pendientes reales |

## Fronteras de confianza

La red privada no reemplaza la autenticación. El PIN vence, se usa una sola vez y está limitado contra intentos repetidos. El token es revocable y viaja dentro de TLS. La aplicación compara la huella de la PC; el usuario debe verificarla al vincular, también al usar un enlace.

El control no acepta comandos arbitrarios, scripts ni rutas ejecutables enviados por una rutina. Una aplicación portable se agrega desde Windows y debe pasar las restricciones del catálogo. Los navegadores solo reciben URLs válidas. La interfaz escapa títulos, nombres y campos de usuario.

Las páginas ajenas no obtienen el puente Android; el panel local rechaza otros hosts/orígenes y las respuestas tienen una política de contenido restrictiva. El token temporal del panel local no autoriza acceso remoto. Las conexiones TCP y el tamaño de solicitudes tienen límites.

Las confirmaciones de energía y finalización tienen propósito, dispositivo y caducidad separados. Revocar un dispositivo impide sus solicitudes y cancela pasos pendientes. No puede deshacer una acción que Windows ya empezó a ejecutar.

La firma de distribución valida la integridad contra una clave conocida. Si alguien reemplaza también el comprobador o controla la PC, esa defensa deja de ser una raíz de confianza suficiente. Windows sigue aplicando sus permisos y advertencias; no se desactivan firewall, UAC, antivirus ni comprobaciones del sistema.

## Lo que no se probó como uso completo

La apertura de una ventana no prueba inicio de sesión, compras, reproducción protegida, partidas, controladores, anticheat, cámara, micrófono o todas las funciones internas de una aplicación. CATALOGO-PRUEBAS.md conserva esas distinciones. Las simulaciones no prueban otro equipo físico ni conectividad de datos móviles.

No se reinició, apagó, suspendió ni bloqueó Windows para esta beta. Las pruebas de energía usan adaptadores aislados. Cierres y finalizaciones se restringen a ventanas creadas por las pruebas; se conservan sesiones existentes y se detiene cualquier recorrido ambiguo.

El acceso remoto requiere PC encendida, sesión iniciada, Eddy Deck y VPN disponibles. Una actualización de Windows, caducidad de cuenta, bloqueo de la red o suspensión profunda de Android puede exigir intervención local. Eddy Deck no incluye encendido remoto, escritorio remoto ni gestión de contraseñas.
