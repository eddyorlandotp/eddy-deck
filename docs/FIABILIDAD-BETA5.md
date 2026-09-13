# Fiabilidad de beta 5

Versión 2.2.3-beta.5. Se probaron fallos combinados con datos aislados, sin ejecutar reparaciones, apagados ni cierres sobre otras aplicaciones de Eddy.

## Cancelación y reparación

Antes, las rutas de reparación iniciaban su efecto antes de cancelar las tareas. Un fallo de SQLite al cancelar podía devolver error después de iniciar la reparación. Ahora se cancelan primero el temporizador de energía y todas las tareas pendientes. Se retiran de la cola en memoria antes de intentar guardar cada cancelación. Si un guardado falla, se intentan los demás, se detiene la cola y se devuelve un error 503. Al reabrir, los estados pendientes que no se pudieron guardar se marcan interrumpidos y no se repiten.

El indicador de reparación se activa antes de iniciar el reparador o escribir la solicitud al supervisor; se libera si ese paso falla. Un fallo del reparador puede conservar el enfriamiento de un minuto para evitar bucles. No se ofrece transacción conjunta entre SQLite, el sistema de archivos y los efectos de Windows: un paso que ya llegó al sistema puede haberse realizado.

## Respuestas de otra PC

La interfaz ya comparaba la conexión al recibir una respuesta directa. Faltaba hacerlo al recibir el comprobante consultado después de perder una respuesta. Ahora también verifica la conexión después de consultar el comprobante y al manejar errores tardíos. El resultado anterior no se presenta como éxito en la PC nueva. El identificador pendiente continúa asociado a la PC de origen.

Dos pulsaciones con identificadores diferentes pueden representar dos intenciones válidas. No se eliminan órdenes distintas por parecido. Ante una respuesta perdida, se conserva el identificador de la misma orden y se consulta su recibo; el receptor evita repetir ese efecto.

## Alcance comprobado

Once casos Python combinan cola y SQLite reales con efectos falsos: tareas activas y pendientes, fallos parciales de escritura, reparación fallida, respuesta perdida y reapertura, y cuatro políticas de monitor entre pasos. Una campaña los repite para variar la programación de hilos. No equivale a cientos de escenarios distintos.

Siete casos JavaScript ejecutan el código de transporte de producción con respuestas controladas. Comprueban pérdida de respuesta, cambio de PC, errores tardíos, conservación del identificador al recrear el contexto y almacenamiento lleno. Este montaje no representa una rotación física de Android ni una prueba con datos móviles.

VALIDACION.md registra resultados, intentos iniciales fallidos, límites y verificaciones posteriores de los instaladores. La beta 4 permanece archivada con sus paquetes originales y pruebas prolongadas.
