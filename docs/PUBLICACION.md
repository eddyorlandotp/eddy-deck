# Publicación del código

Esta instantánea pública parte del código de Eddy Deck 2.2.7-beta.9. Incluye la licencia MIT del código propio y la información de dependencias. No contiene claves de firma, datos de vinculación, perfiles privados, informes crudos del dispositivo ni instaladores personales.

## Cambios exclusivos de esta copia

- Los enlaces al respaldo personal se sustituyeron por `https://drive.google.com/drive/my-drive`. Ese destino abre el Drive de quien inicia sesión; no descarga ni actualiza Eddy Deck automáticamente.
- Los identificadores USB y rutas personales se sustituyeron por ejemplos. Los scripts que contienen `ANDROID_SERIAL_HERE` requieren adaptación explícita al dispositivo de pruebas.
- Se normalizaron los archivos de texto a UTF-8 y saltos de línea LF.
- La documentación histórica resume pruebas de la versión privada; no acredita pruebas realizadas en otros dispositivos. No se incluyen sus informes originales porque pueden contener datos locales.

La aplicación instalada y los paquetes privados de la versión base permanecen sin cambios. Esta publicación de fuentes no es una actualización del producto instalado ni una promesa de compatibilidad universal.

## Compilar una distribución propia

Sigue README y ENTORNO-COMPILACION.md. Crea un entorno Python e instala requirements.txt; prepara las herramientas oficiales con scripts/setup_toolchain.py. Ejecuta las pruebas unitarias, luego compila Windows, Android y finalmente el paquete. Algunas herramientas se descargan durante la preparación.

Las claves privadas no se distribuyen. Los scripts de compilación generan las propias cuando faltan; conserva esas claves fuera de Git. Una firma Android nueva no puede actualizar la instalación privada existente manteniendo su identidad de firma. No reemplaces las claves originales ni desinstales una app con datos sin un respaldo. La clave pública de verificación incluida no permite firmar paquetes.

Configura el destino de tus respaldos de manera coherente antes de generar una nueva distribución: companion/integrity.py, installer/Compatibility.cs, android/src/com/eddy/deck/MainActivity.java, ui/beta2.js, scripts/publish_desktop.py y la documentación. scripts/build_manual.py regenera el manual incorporado. Cada distribución modificada necesita su propia versión, compilación y validación.

## Pruebas y límites

`python -m unittest discover -s tests -v` ejecuta los archivos test_*.py con fixtures y directorios temporales. Los scripts de pruebas reales tienen nombres independientes: inspecciónalos y configúralos antes de ejecutarlos; algunos abren aplicaciones, cambian el volumen o interrumpen redes en el equipo de prueba. No son una prueba automática segura para cualquier equipo sin preparación.

La versión base registró 211 pruebas Python, 63 comprobaciones Android y tres reaperturas con 24 comprobaciones, además de pruebas locales de reconexión. La copia pública pasó de nuevo las 211 pruebas Python el 13 de septiembre de 2026 (14.707 segundos, sin fallos). Las pruebas de Android y hardware de la distribución pública no se han repetido.

Siguen pendientes: datos móviles reales/otra red, un reinicio completo de Windows y otras computadoras. Tailscale requiere conexión y cuenta en ambos dispositivos; el código no garantiza despertar remoto, superar bloqueos de red ni disponibilidad de terceros.
