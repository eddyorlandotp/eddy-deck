# Publicación · Eddy Deck 2.2.11-beta.13

GitHub Releases distribuye los instaladores oficiales de esta beta: Windows, Android y el manifiesto de descarga firmado. El comprobador usa ese origen; no necesita acceso a una cuenta ni al respaldo privado de Drive. Solo descarga entregas completas y verifica su contenido antes de ofrecer instalarlo.

Las fuentes públicas contienen el mismo comportamiento de producto. Los identificadores de USB y rutas personales de scripts de pruebas se sustituyen por ejemplos y los saltos de línea se normalizan. Los instaladores firmados publicados son los mismos verificados para esta entrega. No contienen perfiles, vinculación, claves privadas ni enlaces al Drive personal.

Los informes del dispositivo y la copia original de fuentes se conservan en el respaldo privado. VALIDACION.md distingue controles reales, simulaciones y pendientes. Esta publicación no convierte resultados de esta PC en una certificación de otras computadoras.

## Compilar

Sigue README y ENTORNO-COMPILACION.md: prepara Python, ejecuta las pruebas, compila Windows antes de Android y después empaqueta. El APK lleva el instalador de Windows y el manual. Las pruebas físicas requieren revisar su alcance, configurar el dispositivo y conservar las sesiones existentes.

Las claves de firma no se distribuyen. Una compilación que genere claves propias tendrá una identidad Android diferente y no actualizará la app oficial sobre sus datos. Su verificación también tendrá otra clave: para distribuir un fork configura su propio repositorio y canal de firmas de forma coherente. No desinstales una instalación con datos para saltarte una incompatibilidad de firma.

El archivo EddyDeck-update.json fija versión, tamaño, hash y URL; EddyDeck-update.sig lo firma. Los archivos internos tienen otra verificación firmada. Copiar ambos archivos sin la clave privada no permite crear una actualización válida. Las versiones antiguas permanecen disponibles y no se sobrescriben con otros binarios.

El canal personal incluye las betas publicadas. La versión final, con el mismo número principal, tiene precedencia sobre sus prereleases. No se instala una actualización sin la acción explícita en el comprobador. Consulta ACTUALIZACIONES-GITHUB.md para límites de red, arquitectura y recuperación.
