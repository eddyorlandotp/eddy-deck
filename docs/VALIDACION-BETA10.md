# Validación · Eddy Deck 2.2.8-beta.10

Esta beta corrige la apertura de Roblox/TIDAL en rutinas y añade activación opcional al frente. [APERTURAS-BETA10.md](APERTURAS-BETA10.md) detalla causa, comportamiento y límites. El manual de usuario está separado en [MANUAL-USUARIO.md](MANUAL-USUARIO.md).

Las pruebas de código realizadas abarcan 211 regresiones anteriores y 13 casos nuevos de persistencia, importación, selección de ventanas, minimización, activación y cancelación. La secuencia Windows real de dos aplicaciones completó ambos pasos y verificó sus estados; el informe también registra reaperturas sin duplicar ventanas. Los menús se probaron con solicitudes aisladas: no equivalen a ejecución Windows real.

La entrega incluye por separado los informes beta10-core-tests, beta10-launch-live, beta10-launch-ui, beta10-visual-tests, beta10-claude-review, beta10-release-verification y beta10-final-device-verification. Allí constan resultados definitivos, fuentes y archivos instalados. La revisión externa conserva su alcance y hallazgos; no se presenta como garantía universal.

Pendiente: datos móviles reales y otra red, reinicio completo de Windows, otra PC física, ARM y aplicaciones no observadas. El resultado exitoso de Roblox/TIDAL no certifica todos los programas del catálogo. La política de errores de cada rutina se conserva. Las sesiones existentes no se cierran para probar.

La versión Windows se compila antes de Android, cuyo APK incorpora el instalador y manual actualizados. Los paquetes, código e informes anteriores se conservan. La publicación pública de GitHub excluye claves, datos de vinculación y destinos privados de respaldo; los instaladores personales quedan en el respaldo privado.

Consulta [VALIDACION-BETA9.md](VALIDACION-BETA9.md) para la entrega anterior.
