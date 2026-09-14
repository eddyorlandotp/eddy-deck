# Recorrido de fiabilidad · beta 11

Xbox registra un identificador para abrirse y otro para su ventana. Se añadió la correspondencia exacta, comprobada en su manifiesto instalado, sin asociar otras aplicaciones o widgets de ese paquete.

La campaña surge de fallos encontrados en usos cotidianos: música, aperturas y dos pasos de rutina. El objetivo es ampliar rutas y verificar efectos visibles, no acumular repeticiones de una sola prueba. Un catálogo descubierto o un proceso existente nunca demuestra funcionamiento completo de una app.

## Correcciones

- Selectores universales: Música usaba un menú nativo. La conversión se amplió al documento completo, se corrigió la regla que lo ocultaba y se preserva la selección abierta durante los refrescos. Se comprueban el control visible y el ocultamiento real del anterior.
- Guardados: al fallar validación o escritura se restaura el perfil en memoria. Evita botones fantasma o ediciones fallidas persistidas accidentalmente por otra operación.
- Música: acciones directas y de rutinas comparten validación. Pausar un destino desaparecido da un aviso específico, sin alternar la reproducción de otro programa. La espera de música en una rutina se puede cancelar; los controles directos ocupados tienen plazo de admisión.
- Cancelación: se comprueba también después del último efecto. Un paso que ya actuó queda registrado; cancelar durante ese paso no termina falsamente como rutina completada.
- Aperturas: Blood Strike reveló una llamada bloqueada por permisos. Los accesos directos conservan argumentos y directorio mediante creación de proceso, que informa si necesita elevación. No se solicita ni evita ese permiso. Las llamadas nativas se aíslan, tienen plazo y cancelación.
- Auxiliares: los procesos de apertura y foco esperan a que su receptor los vincule a un trabajo de Windows. Si el receptor desaparece, Windows recoge el auxiliar; las aplicaciones abiertas salen de ese grupo y se conservan. Los auxiliares de TIDAL y sesiones también se vinculan a la vida del receptor.
- Actualización: GitHub pasa a distribuir instaladores verificables; véase ACTUALIZACIONES-GITHUB.md.

## Capas de prueba

| Área | Evidencia y alcance |
|---|---|
| Perfil y catálogo | Añadir, editar, borrar, ordenar, importar, referencias ausentes, errores de validación/disco; pruebas sobre archivos y objetos aislados |
| Rutinas y cola | Pares de tipos de paso, stop/continue, editar o borrar con una ejecución pendiente, cancelación esperando música y durante el último efecto, recibos/reintentos |
| Música | 20 destinos simulados y seis controles por destino; ambigüedad según número reproduciendo, destino perdido, controles no compatibles; reproducción física se documenta aparte |
| Ventanas | Campaña serial sobre el catálogo actual. Por aplicación: descubrimiento, apertura observada, primer plano, minimizar/ventana/maximizar, cierre y requisitos pendientes |
| Seguridad y red | API con entradas inválidas, límites, clientes incompletos, autenticación; pruebas previas se conservan separadas de la ejecución beta11 |
| Monitores | Matriz de geometría con uno a cinco monitores, coordenadas negativas, escalas simuladas, monitor ausente y fallback explícito |
| Interfaz | Cinco tamaños, búsqueda, teclado/Atrás, todos los selectores, formulario inválido, listas largas y 20 reproductores; Android físico separado |
| Instalador | Firma y versión, ZIP hostil, red/orígenes, cancelación, lectura del paquete publicado; no modifica otras apps |
| Procesos propios | Vencimiento y cancelación; prueba mata un receptor de prueba, observa que termina su auxiliar y que permanece la app ficticia, y luego limpia esa app |

## Ventanas y limpieza

Se conserva una línea base de sesiones existentes. Cada ventana nueva de prueba se registra por HWND, PID y fecha de creación antes de cerrarla normalmente. No se confirman diálogos de guardar, inicio de sesión, permisos ni instalaciones ajenas. Un launcher, anuncio o diálogo que aparece aparte provoca revisión antes de abrir la siguiente app. Se revisan de nuevo cierres lentos y ventanas de bandeja. El registro privado de identidad no se publica.

## Límites

La campaña no prueba todas las combinaciones posibles de todas las aplicaciones. Distingue combinaciones generadas, ventanas observadas y acciones reales. No se inventan 20 reproductores instalados: el caso de 20 destinos se provoca con una simulación explícita. Los juegos con pantalla exclusiva pueden rechazar tamaño o primer plano; un aviso correcto no equivale a movimiento verificado. Aplicaciones con permisos, cuenta, hardware o launchers ambiguos quedan identificadas para revisión manual.

Datos móviles sin saldo, otra red física, otra PC/ARM, monitor desconectado físicamente, cambio real de DPI y reinicio completo de Windows conservan su condición de pendientes si no existe informe que confirme lo contrario. Por ello la entrega conserva la denominación beta. No se afirma ausencia de errores ni aprobación final de código por Claude: su revisión fue de una copia anterior y sus hallazgos se resolvieron y probaron por Codex.
