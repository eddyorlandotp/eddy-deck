# Componentes de terceros

El código de Eddy Deck usa licencia MIT. Los componentes incluidos conservan sus licencias; la licencia del proyecto no reemplaza las de terceros.

Los textos se copian sin modificar a `licenses`, con nombres cortos para evitar rutas excesivamente largas al instalar. `licenses/INDICE.json` relaciona cada copia con su paquete, versión, ruta original y hash. El código de pystray y la licencia de Python también se conservan.

- Python: PSF License. El entorno se incluye en el paquete de Windows mediante PyInstaller.
- PyInstaller: GPL con excepción para distribuir aplicaciones empaquetadas. La aplicación resultante conserva su licencia MIT.
- cryptography: Apache 2.0 o BSD. Incluye sus componentes criptográficos.
- pywin32: licencia PSF y avisos de sus autores.
- Pillow: licencia HPND.
- qrcode: BSD.
- pystray: LGPL 3.0. Se distribuye como dependencia separada empaquetada; su código fuente está disponible en https://github.com/moses-palmer/pystray y se conserva una copia del código Python de esa versión con los avisos de distribución.
- Android Platform Tools / ADB: herramientas oficiales de Google; los avisos originales se conservan en `usb/NOTICE.txt`. Solo se utiliza ADB para instalar o abrir Eddy Deck y crear su enlace USB. No se usa fastboot.
- Android SDK Build Tools, plataforma Android 35 y Microsoft OpenJDK 17: utilizados durante compilación. No se incluyen completos en los instaladores. `setup_toolchain.py` registra las fuentes y hashes en `.build/tools/sources.json`.

No se incluyen fuentes, imágenes, bibliotecas ni scripts alojados en CDNs dentro de la interfaz. Los símbolos son SVG del propio proyecto. Los nombres de aplicaciones ajenas identifican las aplicaciones instaladas en la PC.
