# Entorno de compilación y mantenimiento

Eddy Deck 2.2.3-beta.5, observado el 12 de septiembre de 2026. El instalador Windows incluye el intérprete y las dependencias necesarias para ejecutar Eddy Deck. No requiere que el usuario instale Python, Java ni el SDK Android. Tailscale sigue siendo una aplicación externa para el acceso privado por internet.

## Herramientas de esta entrega

| Componente | Versión observada |
| --- | --- |
| Python de compilación Windows | 3.14.1, 64 bits |
| PyInstaller | 6.22.2 |
| cryptography / qrcode | 50.0.1 / 8.2 |
| Pillow / pystray / pywin32 | 12.3.0 / 0.19.5 / 312 |
| Microsoft OpenJDK | 17.0.20.1 |
| Plataforma de compilación Android | API 35, revisión 2 |
| Android Build Tools | 35.0.0 |
| Android Platform Tools / ADB | 37.0.1 |
| Versión Android mínima declarada | API 26 |

`requirements.txt` fija las dependencias directas. `beta4-build-environment.json`, dentro de las evidencias, conserva las versiones de los 17 paquetes presentes en el entorno, las fuentes oficiales registradas al preparar las herramientas y SHA-256 de ocho archivos de herramientas. No contiene claves de firma, rutas personales ni identificadores del celular.

El manifiesto de descargas conserva el algoritmo original: los archivos Android se comprobaron con los SHA-1 publicados en el manifiesto de Google, y el JDK con SHA-256. Los SHA-256 adicionales del informe se calcularon sobre las herramientas locales; no se presentan como firmas del proveedor.

## Reconstrucción

Sigue los comandos de desarrollo de README.md. El orden de entrega es Windows, Android y paquetes. Android incorpora el instalador Windows y la documentación recién compilados; el verificador compara esos archivos con la entrega. `scripts/capture_build_environment.py` genera el inventario del entorno que se esté usando.

Conservar las versiones facilita investigar cambios, pero no garantiza reconstruir binarios idénticos byte por byte: influyen las herramientas, sus dependencias, metadatos y firmas. Los hashes de una entrega sirven para comprobar esa entrega concreta. Una entrega con cambios necesita una versión nueva.

## Actualizaciones futuras

No actualices dependencias mientras se ejecuta la prueba final de una versión. Una actualización requiere revisar compatibilidad, repetir las pruebas pertinentes, reconstruir Windows y Android y conservar la versión anterior. Que otra aplicación cambie de nombre, ruta, ventana o lanzador puede requerir resincronizar el catálogo y revisar su asociación; no se promete compatibilidad automática con futuras versiones de programas ajenos.

El ZIP de pruebas también forma parte del respaldo. `package_evidence.py` reúne informes actuales e históricos: para reutilizar los históricos deben conservarse sus JSON en `artifacts` o extraerse desde `Informes` del ZIP. El control está configurado para beta 4 y se detiene si cambia la versión sin actualizar su matriz de ensayos. Construir los instaladores con los scripts de Windows y Android no requiere esos informes históricos; publicarlos como una entrega validada sí exige las evidencias correspondientes.

Las claves originales de actualización permanecen en `private` del proyecto, fuera de los paquetes para compartir. Para poder firmar una actualización compatible deben conservarse de forma privada; el código público no sustituye esas claves. Los instaladores existentes y la edición de botones no requieren acceso a ellas.
