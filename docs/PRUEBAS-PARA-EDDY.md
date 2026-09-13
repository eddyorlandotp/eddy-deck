# Pruebas de uso para Eddy

La beta trae pruebas automáticas y evidencias técnicas. Esta lista sirve para probarla en situaciones que necesitan tu uso real o hardware que todavía no tenemos. No hace falta completarla de una vez.

## 1. Uso normal y rutinas

Crea una rutina con dos aplicaciones que puedas abrir sin documentos importantes: elige pantallas, un tamaño y una espera corta. Ejecútala, revisa Cola y resultados y vuelve a tocar la misma rutina mientras está pendiente. Debe conservar una sola copia pendiente. Cuando termine, una nueva pulsación sí puede ejecutarla otra vez.

Después pon la cola en pausa, envía dos rutinas distintas, cancela una y reanuda. Solo debe ejecutarse la que conservaste. Editar una rutina ya enviada no modifica esa ejecución: cancela y envía de nuevo si quieres aplicar tus cambios.

## 2. Aplicación ya abierta

Prueba un botón con «Usar su ventana existente». Minimiza esa ventana y vuelve a abrirla desde el botón: si es la única identificada, debe restaurarse. Con varias ventanas, selecciónala desde Mi PC. Una URL guardada sí se envía al navegador.

Prueba Proteger en una ventana sin trabajo importante. Eddy Deck debe rechazar su movimiento/cierre hasta que quites la protección. Cerrar normalmente puede dejar un aviso de guardar en la PC; no significa que haya fallado la conexión. No pruebes Finalizar con documentos que quieras conservar.

## 3. Datos móviles, cuando tengas datos

Primero confirma que una página normal abre en el celular usando solo datos. Mantén Windows despierto, con sesión iniciada, Eddy Deck y Tailscale activos. Activa la VPN de Tailscale en el teléfono, retira USB y apaga Wi-Fi. Comprueba una lectura de Mi PC y una apertura sencilla.

Alterna entre Wi-Fi y datos y revisa que reconecte sin volver a vincular. Si una acción quedó incierta, revisa su resultado antes de repetirla. Cambiar de red no debe enviar la orden a otra PC. Esta prueba sigue pendiente mientras no haya datos móviles disponibles.

## 4. Laptop y monitores

En otra laptop prueba primero con Principal y una sola pantalla. Después conecta un monitor, actualiza Mi PC y prueba una rutina con «Usar la principal si falta». Desconecta ese monitor y verifica la alternativa. Con «Detener y avisarme», debe informar la ausencia.

Si usaste una pantalla fija, revisa la selección después de cambiar PC, dock o cableado: se guarda un identificador de Windows, no una huella física permanente. Cerrar la tapa puede suspender la laptop según su configuración; una PC suspendida no recibe órdenes.

## 5. Otra computadora

Guarda el instalador Windows desde Mis PCs o descárgalo de tu Drive privado. Extrae todo en una carpeta corta y abre el comprobador. Si rechaza Windows, archivos o espacio, guarda su informe; no mezcles DLL de otra versión ni desactives protecciones.

Instala y vincula esa PC con su propio código y huella. Sus apps deben aparecer al sincronizar. Importa tu copia del panel, revisa referencias faltantes y pantallas y prueba una rutina sencilla antes de usar combinaciones largas. No copies claves ni permisos de la primera PC.

## 6. Exportación y recuperación

Guarda una copia de tu panel y el manual en Descargas. Empieza con almacenamiento local; una ubicación en la nube depende también de su proveedor de archivos y de internet. Conserva el ZIP de Windows y el APK de la misma versión.

Usa Reiniciar conexión de Windows cuando el receptor responde pero se comporta mal. Usa Reparar archivos si la comprobación detecta daño. Reparar no reinicia Windows ni cierra tus otras aplicaciones. Guarda los formularios que estabas editando antes de reparar el celular.

## 7. Qué anotar si encuentras un fallo

Guarda el informe desde la app y escribe:

- Qué esperabas y qué ocurrió.
- Botón o rutina utilizada, y qué paso quedó marcado.
- Si la app ya estaba abierta y cuántas ventanas tenía.
- USB, Wi-Fi o Tailscale; si cambió la conexión durante la acción.
- Pantallas conectadas y destino elegido.
- Versiones de Eddy Deck en el celular y la PC.

No incluyas códigos de vinculación, contraseñas ni claves. Un informe no debe enviarse a nadie automáticamente. Conserva la versión anterior y revisa VALIDACION.md para distinguir una función pendiente de una regresión nueva.
