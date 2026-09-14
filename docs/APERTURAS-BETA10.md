# Aperturas y primer plano · beta 10

## Corrección comprobada

La rutina real tenía Roblox en el primer paso (principal, maximizada) y TIDAL en el segundo (izquierda, maximizada), con política de detener ante un error. El registro mostraba fallo de tamaño fijo en el primer paso: el segundo nunca se intentó. El estilo de Roblox carecía de WS_THICKFRAME y WS_MAXIMIZEBOX; una prueba nativa confirmó que acepta SW_MAXIMIZE. Se retiró esa deducción para maximizar y se conserva la verificación del estado y monitor resultantes. La restricción prudente para mitades de pantalla permanece.

## Comportamiento

`activation` acepta `front` y `windows` en botones y pasos de apertura. La ausencia del campo significa `front`; al importar y editar se conserva. No cambia el esquema 2. La capacidad `launchForeground` permite al panel explicar que una PC anterior necesita actualizarse. La opción se transmite también desde la apertura con monitor preguntado y URL temporal.

Las aperturas al frente esperan una ventana identificable, incluidas las que conservan monitor y tamaño. Se rechazan selecciones ambiguas; no se repite la apertura por tiempo de espera. Las ventanas existentes se reutilizan, restauran si corresponde y activan. Abrir minimizada conserva ese estado. Mover y música no piden activación.

La solicitud de foco comprueba el resultado y no usa TOPMOST, teclas sintéticas, cambios globales de Windows ni elevación. La activación se ejecuta en un proceso auxiliar separado con 2.5 segundos de límite. Ante cancelación o vencimiento se termina únicamente ese auxiliar y se espera su salida; no queda un hilo pendiente que pueda activar otra ventana después. La unión temporal de colas de entrada se libera al terminar el auxiliar. Si Windows rechaza el foco, se devuelve needs_attention; la rutina termina con avisos sin ocultar lo ocurrido ni repetir aperturas. La política stop sigue deteniendo errores reales de pasos; la interfaz explica los pasos no ejecutados.

## Evidencias y límites

Se reprodujo el fallo original mediante el registro y se comprobó la maximización nativa. La secuencia real de dos aplicaciones terminó, ambas maximizadas, con TIDAL al frente al finalizar. Se probaron también reutilización, minimización explícita y las dos opciones de activación sin cerrar sesiones del usuario ni modificar su rutina guardada. Las pruebas de interfaz verifican guardados, cambios de tipo, apertura con monitor preguntado, versión antigua de PC y aviso de pasos omitidos. Las regresiones Python incluyen persistencia, importación, cancelación y ambigüedad.

Los informes beta10 de la entrega registran los resultados y hashes finales. Las pruebas de interfaz con respuestas simuladas están separadas de Windows real y Android instalado. No se asegura activación sobre escritorios seguros, apps bloqueadas, juegos de pantalla completa exclusiva ni ventanas siempre encima. No se hizo un reinicio completo de Windows ni la prueba pendiente con datos móviles reales/otra red.

Referencia del comportamiento de Windows: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow
