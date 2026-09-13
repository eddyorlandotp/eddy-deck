# Cambios de la beta 2

Versión 2.2.0-beta.2. La prioridad de esta entrega es la recuperación y la coherencia de las acciones.

## Uso y recuperación

- Controles de ventanas existentes: reutilizar, restaurar, minimizar, proteger, cerrar normalmente y finalizar con confirmación independiente. La protección es de sesión.
- Pausar las tareas siguientes, cancelar sin bloquear música y conservar la instantánea de una rutina ya enviada.
- Comprobador Windows independiente del Python empaquetado, verificación RSA/SHA-256, detección de dependencias faltantes y copia local de reparación.
- Restauración explícita de un JSON del panel aunque el archivo actual esté corrupto, conservando el original y los vínculos.
- Respaldo privado en Drive, instalador Windows separado, manual completo dentro del celular y documentación técnica separada.
- Aviso de versiones distintas y controles desactivados cuando la PC no anuncia su compatibilidad.

## Fallos corregidos o contenidos

- La política de continuar/detener ya forma parte de la deduplicación de rutinas.
- La admisión de trabajos se coordina con reparación y acciones de energía.
- La salud del receptor detecta una cola que perdió su registro duradero.
- Un fallo al consultar pantallas no elimina la lectura independiente de ventanas.
- Un vínculo se guarda en disco antes de incorporarse a la lista activa.
- Una ventana cerrada o reemplazada no se controla usando una identidad antigua.
- Las copias conservan referencias de aplicaciones usadas, admiten paneles extensos y pueden asociar una aplicación actualizada cuando su identidad o nombre es inequívoco.
- Las respuestas atrasadas no borran el recibo de una acción posterior; un resultado incierto no provoca la repetición automática de la acción.
- Las tareas de conexión, gestión local y escritura de archivos de Android están separadas y limitadas. Una escritura ya aceptada puede terminar al reconstruir la pantalla.
- Las exportaciones grandes guardan referencias pequeñas en el estado de Android. El selector de archivos tiene manejo de error y no reemplaza otra exportación pendiente del mismo tipo.
- El cambio de PC interrumpe reintentos hacia la anterior y se comprueba al importar una copia.
- El redescubrimiento de una dirección requiere verificar la identidad TLS conocida; una respuesta broadcast no basta.
- Las licencias conservan su contenido y procedencia con rutas más cortas, evitando un fallo de copia observado al preparar una instalación en una ruta profunda.

## Evidencia y alcance

VALIDACION.md contiene los resultados medidos de esta entrega; VALIDACION-BETA1.md conserva la historia. CATALOGO-PRUEBAS.md distingue descubrimiento, apertura y movimiento de las aplicaciones. Ninguna simulación se presenta como prueba física de otra laptop, Windows ARM, datos móviles o uso completo de todos los juegos y reproductores.

No hay actualización automática desde Drive ni una garantía de ausencia de fallos. Los paquetes, informes y versiones anteriores se conservan para comparar cambios y recuperar una copia conocida.
