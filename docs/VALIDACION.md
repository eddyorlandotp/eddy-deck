# Validación de Eddy Deck 2.2.7-beta.9

Esta campaña trata la pérdida de conexión después de arrancar Windows, los cambios de red y la selección segura de rutas. No certifica de nuevo todos los motores de aplicaciones. La campaña anterior está conservada en VALIDACION-BETA8.md.

## Causa y correcciones

Se observó un receptor beta8 iniciado por Explorer con certificado distinto al que el Samsung tenía vinculado. GetFinalPathNameByHandleW confirmó que Codex leía una copia de AppData dentro de su paquete MSIX. El arranque normal usaba otra copia. Se migró la identidad que coincide con el teléfono a `%USERPROFILE%\.eddydeck`, verificando hashes de certificado, llave, dispositivos y panel. Se conservaron las carpetas anteriores. Tailscale tampoco estaba activo en Android; se habilitó VPN siempre activada y la PC observó al teléfono en línea.

Además se reemplazó la enumeración principal basada en nombre/DNS por interfaces de Windows; heartbeat autenticado aprende direcciones recién agregadas, se refrescan cada 10 segundos y el detector UDP se recupera de errores. Android descubre por la red Wi-Fi explícita, verifica el certificado exacto y termina la lectura en la misma llamada. Solo las comprobaciones de lectura prueban varias rutas: una orden ya enviada no se repite por otra IP si se pierde la respuesta.

## Evidencia de esta entrega

Los archivos siguientes se generan durante el cierre de la campaña. El empaquetador exige los resultados actuales: una entrada en esta tabla no sustituye un resultado aprobado.

| Área | Archivo | Alcance |
| --- | --- | --- |
| Migración e identidad vinculada | beta9-data-migration.json; beta9-original-pair-confirmed.json | Copia transaccional, ubicación física comprobada, vinculación original sin sustituir |
| Regresión de lógica | beta9-core-tests.json | Pruebas aisladas sobre código actual, migración interrumpida, identidad incompleta, dos migradores, cambios de interfaces, heartbeat autenticado y recuperación UDP |
| Interfaz | beta9-visual-tests.json; beta9-media-ui-tests.json; beta9-offline-ui-tests.json | Menús/controles con efectos simulados, reconexión sin volver a solicitar código |
| Android instalado | beta9-android-installed-tests.json | Bóveda aislada, cambio de PC, descubrimiento falsificado, VPN tardía, respuesta POST perdida y recreación de actividad |
| Conexión instalada | beta9-live-reconnection.json | Identidad TLS servida y guardada, arranques del receptor, rutas LAN/VPN, reapertura y cortes provocados, con alcance exacto en cada caso |
| Instalación y copias | beta9-release-verification.json; beta9-final-device-verification.json | Archivos firmados, APK/instalador/documentación coherentes y perfil/vinculación conservados |
| Drive privado | beta9-drive-verification.json | Metadatos releídos de nombre/tamaño/carpeta y permisos; hashes de originales locales, no comparación de descarga remota |

## Fallos encontrados durante los ensayos

- La migración inicial de SQLite dejaba manejadores abiertos en Windows; se corrigió su cierre explícito y se comprobó que el directorio se publica sin archivos bloqueados.
- Android rechazó `Network.bindSocket` con EPERM cuando Tailscale estaba activo. El descubrimiento tiene ahora una alternativa por la ruta de sistema; después encontró la identidad esperada y recuperó una dirección obsoleta en la misma llamada (4,4 s en el ensayo inicial).
- Una migración automática podía copiar datos de un receptor antiguo activo. Se comprueban los puertos antes de copiar y de publicar; se conserva todo y se solicita cerrar Eddy Deck si el receptor está activo.

- Se corrigieron los avisos de inicio para errores de permisos/datos y la versión del diagnóstico Android, detectados por Claude. La versión se lee ahora de la aplicación instalada.

- El receptor aislado de pruebas podía ocupar UDP 47991 durante un reinicio del producto. El descubrimiento ahora se inicia solo para el puerto de producción; las instancias de prueba en otros puertos no lo anuncian ni lo reservan. Se repitieron las pruebas de red con el servicio aislado cerrado.

## Límites

No se reinició Windows ni se cerraron aplicaciones del usuario para esta campaña. Un arranque del receptor desde Explorer no certifica todos los escenarios de arranque del sistema. Sin saldo móvil no se certifica tráfico por datos reales ni una conexión desde otro país. Los cortes simulados y las rutas privadas probadas se distinguen en el informe. Otra PC/laptop, aislamiento Wi-Fi, Windows ARM, políticas empresariales y Tailscale sin internet/cuenta válida permanecen como límites. No hay despertar remoto ni control previo al inicio de sesión de Windows.

Claude Code revisa solamente el código; Codex integra y ejecuta las pruebas. Sus hallazgos y su resolución se conservan en beta9-claude-final y beta9-review-resolution. Ninguna revisión equivale a demostrar que jamás habrá fallos.
