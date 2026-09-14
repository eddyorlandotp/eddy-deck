# Desarrollo de Eddy Deck

Priorizar fiabilidad sobre nuevas funciones. Mantener el manual de usuario separado del informe técnico. Registrar por separado pruebas unitarias, descubrimiento, apertura observada, movimiento verificado y casos pendientes. Un proceso o una entrada del catálogo no prueba el funcionamiento completo.

En pruebas reales, cerrar solo ventanas creadas por la propia prueba. Conservar sesiones existentes y detenerse ante permisos, documentos pendientes o estados ambiguos. Reparar Eddy Deck no significa reiniciar Windows ni cerrar otras aplicaciones.

Para nuevas entregas de producto: incrementar versión, actualizar README y docs/VALIDACION.md, ejecutar las pruebas pertinentes y compilar Windows antes de Android (el APK lleva el instalador Windows). Empaquetar con scripts/package_release.py. No reemplazar una versión entregada por binarios distintos.

No publicar private/, claves, tokens, datos de vinculación, informes personales ni destinos privados de respaldo. GitHub Releases contiene los instaladores oficiales; los perfiles y respaldos del propietario siguen siendo privados. Ver docs/PUBLICACION.md.
