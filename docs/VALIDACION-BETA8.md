# Validación de Eddy Deck 2.2.6-beta.8

Esta entrega pule diseño y menús de edición. No modifica los motores de música, lanzamiento, ventanas ni el protocolo. La campaña funcional anterior está conservada en VALIDACION-BETA7.md y MATRIZ-FUNCIONES-BETA7.md; no se presenta como ejecutada de nuevo por cambiar el aspecto.

## Alcance y resultados verificables

| Área | Evidencia | Qué demuestra |
| --- | --- | --- |
| Interfaz actual | beta8-visual-tests.json | Navegación y menús reales en Edge con receptor simulado: tamaños 320/360/412/915/1440, teclado, búsqueda, selección/validación, FormData, borradores, reordenación, opciones incompatibles, texto seguro y ampliación |
| Contraste y fuentes | beta8-design-checks.json | Contraste de combinaciones principales, fuentes locales y diferencias acotadas del backend/Android respecto de beta7 |
| Regresión de lógica | beta8-core-tests.json | Suite de Python sobre fuentes actuales, independiente de aplicaciones del usuario |
| Controles existentes de música | beta8-media-ui-tests.json | Interfaz con efectos aislados y destinos explícitos; no equivale a nuevos ensayos físicos de todos los reproductores |
| Samsung instalado | beta8-phone-design-tests.json | Menús propios, Atrás, búsqueda y borrador en la app instalada; capturas reales y hash del APK |
| Android | beta8-android-installed-tests.json | Instrumentación y recreación de actividad sobre la instalación final |
| Paquetes e instalación | beta8-release-verification.json | Windows firmado e instalado, assets UI/Windows/docs integrados en APK, fuentes y conservación de perfil/vinculación |
| Copias | beta8-final-device-verification.json y beta8-phone-copies-verification.json | Hashes leídos desde el teléfono y coherencia de archivos |
| Publicación | beta8-drive-verification.json | Nombres/tamaños/carpeta/permisos privados releídos desde Drive; los hashes son de los originales locales, sin comparación de descarga remota |

Estos archivos se generan al ejecutar las pruebas de esta entrega. El empaquetador rechaza la publicación si faltan los informes obligatorios, no corresponden a las fuentes actuales o al APK final, o indican fallo. Las capturas y los informes de cierre se entregan también por separado para evitar hashes circulares.

## Fallos encontrados durante este pulido

- El diseño anterior dependía de selectores nativos básicos y usaba herramientas de pasos de 28×32 px. Los menús de edición ahora tienen su propia lista, y las herramientas miden 44 px.
- Un diálogo con altura en 100dvh se salía de la pantalla al ampliar CSS al 150%. Se reprodujo; usar un límite relativo al contenedor mantiene el diálogo dentro y permite desplazarse.
- Las pruebas conservaron errores de herramienta por clic en una opción deshabilitada y codificación local de texto. Se corrigió el arnés y se restauró Java desde la entrega anterior antes de aplicar sus cuatro cambios de color y la ruta local explícita del nuevo selector. No se interpretaron esos errores como fallos de controles de Windows.

- En una rutina larga, Agregar paso heredaba desplazamiento y ocultaba el encabezado. Se restablece la posición al cambiar de formulario; una secuencia de 18 pasos lo comprueba.
- En Android, el selector de aplicación perdía su etiqueta al compartir contenedor con un buscador. Se toma ahora la etiqueta visible del campo; el menú anuncia Aplicación.

## Límites vigentes

Datos móviles, otra PC/laptop, monitores conectados físicamente a media sesión, Windows ARM y TalkBack siguen sin certificación física en esta campaña. Windows Media Player Legacy conserva pendiente su asistente inicial. El catálogo no certifica aplicaciones. No se ejecutan apagado, reinicio, suspensión ni bloqueo durante el pulido. Los cuadros del sistema y Música mantienen sus selectores nativos. No se afirma ausencia total de errores.

Claude aporta propuesta y revisión de solo lectura; Codex integra y contrasta los hallazgos. El estado exacto de esa revisión y sus límites están en beta8-claude-* y beta8-review-resolution.json.
