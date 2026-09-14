# Instaladores y actualizaciones desde GitHub

Desde beta 11, el origen es [GitHub Releases](https://github.com/eddyorlandotp/eddy-deck/releases). Drive sigue conservando respaldos privados. Ningún token de GitHub/Google ni vínculo personal se distribuye en la aplicación.

El comprobador independiente incluye **Buscar y descargar de GitHub**. Consulta hasta 30 entregas, descarta borradores, versiones solo de código y entregas con archivos incompletos. Elige la versión más alta publicada con el paquete y su manifiesto firmado. Esta aplicación personal sigue el canal de pruebas: se incluyen versiones alpha/beta/rc identificadas; una versión estable precede a sus pruebas en el orden de actualización. No se instala silenciosamente: al terminar la descarga se ofrece Instalar / reparar.

Cada entrega distribuible contiene `EddyDeck-update.json`, `EddyDeck-update.sig`, el ZIP Windows y el APK con la misma versión. `scripts/build_update_manifest.py` firma el nombre, URL exacta, versión, arquitectura, requisito de Windows, tamaño y SHA-256 del ZIP. La clave privada persistente permanece en `private`; el comprobador incorpora únicamente la clave pública. Los ZIP de código que GitHub crea automáticamente no sirven como instaladores.

La descarga está limitada a cinco minutos, 15 segundos por espera de red, cuatro redirecciones y 500 MB. Solo usa HTTPS, el repositorio fijo y los hosts de archivos de GitHub admitidos. Primero valida la firma de la información de descarga; luego compara tamaño y SHA-256 del ZIP; después extrae en una carpeta nueva y comprueba el manifiesto firmado de Windows y todos sus archivos. Rechaza rutas relativas peligrosas, enlaces, nombres reservados, duplicados y archivos extra. No extrae sobre la instalación actual. Cancelar o fallar elimina únicamente la carpeta temporal propia; cerrar la ventana espera la cancelación.

Una comparación completa distingue números de beta y versiones estables: no permite reparar con una versión anterior. La instalación dispone de exclusión mutua. Los procesos iniciados por el comprobador para validar el panel o instalar tienen límites y se recogen al vencer; una operación interrumpida exige revisar el informe y conservar la copia anterior. La instalación prepara la nueva carpeta y conserva la anterior; no reemplaza vínculos ni permisos de celulares. La reparación local sigue funcionando sin internet.

Si GitHub está caído, limita consultas, no tiene paquete compatible o se corta la conexión, se muestra el error y se conserva la instalación. No se convierte un fallo en una descarga de origen diferente. Puede usarse manualmente la copia del teléfono o del respaldo privado. Una nueva clave de firma requiere una migración explícita; nunca se acepta una clave indicada por la propia descarga.

La prueba local del descargador usa una clave desechable para provocar firmas, versiones, URLs y ZIP inválidos. La prueba de descarga pública se registra aparte contra la entrega real; no debe inferirse de esas simulaciones.

Referencias: [API de entregas de GitHub](https://docs.github.com/en/rest/releases/releases#list-releases), [archivos de entregas](https://docs.github.com/en/rest/releases/assets).
