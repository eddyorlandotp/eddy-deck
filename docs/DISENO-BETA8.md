# Diseño y controles · beta 8

## Dirección visual

Interfaz clara inspirada en escritorios Linux cuidados: fondo suave, grafito, acento verde oscuro y tarjetas pastel. Navegación flotante en celular, panel lateral en escritorio, espaciado consistente y controles táctiles más amplios. Sin dependencias de red, fuentes externas, biblioteca de widgets ni IA durante el uso.

## Implementación

- `ui/styles.css`: capa Beta 8 para componentes, menús, formularios, foco y tamaños adaptables. Los diálogos limitan su altura con porcentajes para no recortarse al ampliar el contenido.
- `ui/pickers.js`: mejora progresiva de los selectores dentro de formularios. El select original sigue conservando name, id, value, required y FormData. El menú propio usa un diálogo etiquetado, listbox, opciones seleccionadas/deshabilitadas y foco de teclado. Atrás cierra primero el menú. Los nombres se insertan como texto.
- Los campos de aplicación y política de apertura siguen siendo los de `extended.js` y `beta2.js`; no se sustituyen las reglas del receptor. Los pasos numerados conservan sus tres acciones existentes.
- Android actualiza colores, versión y la ruta local permitida de pickers.js; Windows sirve ese mismo archivo por una ruta explícita. El comportamiento de conexión, servicio y mantenimiento de pantalla encendida sigue vigente.

## Comprobaciones y evidencias de entrega

La puerta de publicación exige pruebas del código actual, interacción con los nuevos menús en el Samsung instalado, instrumentación Android, integridad Windows, copia del APK y documentación idéntica en los paquetes. Los resultados y hashes están en `Informes/beta8-*` dentro del paquete de pruebas.

`tests/visual_beta8.cjs` recorre Inicio/Rutinas/pasos, formularios y menús a 320, 360, 412, 915 y 1440 px. Comprueba Escape, búsqueda, validación de aplicación ausente, valores de FormData, cambios de tipo, reordenación, opciones incompatibles, HTML malicioso, ampliación 150% y movimiento reducido. Usa estado y respuestas aislados: no controla aplicaciones de la PC.

Se conserva una comparación visual con datos de ejemplo, separada de las capturas del teléfono. Las capturas no demuestran por sí solas efectos sobre Windows. La revisión de Claude es de solo lectura: su propuesta, veredicto y diferencias posteriores se entregan junto con las resoluciones de Codex.

## Límites

Se mantiene el tema claro; no hay selector de temas. El menú propio cubre los formularios, no cambia los cuadros de permisos, exportación ni el selector principal de Música. La prueba de teclado no certifica TalkBack ni todos los lectores de pantalla. La ampliación CSS 150% es una prueba de estrés de disposición, no una certificación de todos los tamaños de letra Android. No se certifican otras computadoras, datos móviles sin saldo, todos los reproductores ni todas las resoluciones físicas por renovar la estética. Consulta también MATRIZ-FUNCIONES-BETA7.md para la evidencia funcional anterior.
