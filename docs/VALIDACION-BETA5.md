# Validación de Eddy Deck 2.2.3-beta.5

Esta entrega corrige dos fallos demostrados mediante pruebas combinadas: reparación que iniciaba su efecto antes de fallar al cancelar tareas, y comprobantes tardíos de una orden al cambiar de PC. FIABILIDAD-BETA5.md explica el diseño. MANUAL-USUARIO.html es el manual práctico separado de este informe.

## Pruebas anteriores a compilar

| Ensayo | Resultado y alcance |
| --- | --- |
| Regresión Python completa | 163 pruebas aprobadas; beta5-core-tests.txt y .json. Datos aislados y efectos de Windows controlados. |
| Fallos combinados | 11 casos aprobados; beta5-combined-tests.txt. Incluyen una rutina activa, tres tareas pendientes, fallo de una o de todas las escrituras, reparación fallida y dos reparaciones concurrentes. |
| Campaña de repetición activa | 30 repeticiones de los 11 casos, 330 comprobaciones; beta5-daily-campaign.json. No son 330 escenarios distintos. El informe exige fuentes de producción idénticas al cierre. |
| Respuestas perdidas y PC seleccionada | 7 casos JavaScript aprobados; beta5-ui-combined-tests.json. Código de producción con transporte sintético en un contexto JavaScript aislado. |
| Interfaz en navegador | 16 recorridos y 13 regresiones aprobados, sin errores JavaScript; beta5-ui-tests.json y beta5-ui-regressions.json. Resoluciones 1280, 412 y 320 píxeles, receptor aislado sin acciones físicas. |
| HTTP adversarial | 90 comprobaciones sin fallos; beta5-http-tests.json. Cuerpos inválidos, autenticación, límites y clientes TLS incompletos; no se envían acciones a la PC personal. |
| Geometría | 1,000 topologías y 17,969 aserciones; beta5-monitor-tests.json. Datos geométricos simulados, incluidos destinos ausentes. |
| Ventanas reales de prueba | 20 comprobaciones; beta5-windows-controls.json. Movimiento, minimizar, restaurar, protección, rechazo del cierre con datos pendientes y finalización confirmada, exclusivamente en ventanas creadas por ese ensayo. |

El caso de desconexión de monitor usa una barrera entre pasos: la primera apertura avisa que empezó, el ensayo retira el monitor del inventario y libera la rutina. Se comprobaron las cuatro combinaciones de destino ausente (detener/principal) y política de rutina (detener/continuar). Usa la cola y el resolvedor reales con apertura simulada; no prueba un cable retirado físicamente ni DPI real.

La pérdida de respuesta seguida de reapertura del receptor se prueba con SQLite real. Repetir el mismo identificador recupera el recibo y conserva un solo efecto simulado. La prueba JavaScript verifica también conservación del identificador al recrear su contexto, ausencia de envío cuando falla el almacenamiento y rechazo de errores o recibos de otra PC. Recrear ese contexto no equivale a girar físicamente Android con una petición real en vuelo.

## Intentos fallidos conservados

beta5-before-fix-tests.txt contiene cinco fallos entre los seis casos iniciales. El conjunto demuestra problemas en el orden de reparación y cancelación; no son cinco defectos independientes. beta5-ui-before-fix.txt demuestra el comprobante tardío presentado sin revisar la PC seleccionada. Sus repeticiones tras corregir pasan.

beta5-combined-initial-fixture-tests.txt conserva un error del montaje: el adaptador de apertura no incluía su campo message. beta5-core-initial-fixture-tests.txt conserva un plazo de inicio de un segundo que venció bajo carga y afectó la siguiente subprueba. El montaje final espera hasta cinco segundos y libera la barrera antes de comprobar el resultado. beta5-ui-initial-version-tests.txt detectó que faltaba regenerar el manual integrado después de incrementar la versión. Se regeneró antes de repetir la interfaz. Ninguno de estos tres casos se presenta como un fallo nuevo del producto.

## Revisión independiente

Claude Code revisa copias de solo lectura; Codex integra. Los informes beta5-peer-* preservan el contenido, fecha y alcance de cada copia. La primera revisión de reparación no encontró un defecto de código ni un ciclo de bloqueos, pero señaló que el archivo de pruebas ya contenía diez métodos y los informes adjuntos solo seis. Se conserva ese dictamen. Los resultados completos posteriores y la comparación de fuentes permiten cerrar esa diferencia de evidencias; no se cambia retrospectivamente el texto del revisor. Otra revisión aborda específicamente la respuesta tardía al cambiar de PC. El dictamen final y las limitaciones están en los informes entregados.

## Instalación y comprobaciones posteriores

Windows se compila primero. El APK Android incorpora exactamente ese instalador, la interfaz y la documentación. Tras instalar se ejecutan las comprobaciones Android normales y tres recreaciones de Activity, y se vuelve a abrir Eddy Deck inmediatamente. beta5-android-installed-tests.json registra el número real ejecutado y la versión instalada.

release-verification compara la firma y archivos de Windows, fuente, APK, documentación, recursos incrustados, accesos directos, inicio automático y conservación del panel, vinculaciones y certificado. final-device-verification compara por SHA-256 el APK instalado y las copias del teléfono. La copia por USB se identifica expresamente: no es una prueba del selector nativo.

La publicación exige además una observación posterior limpia de 90 segundos sobre beta 5, con autenticación reciente, identidad TLS, servicio Android y pantalla encendida si Eddy Deck sigue en primer plano. Sus resultados se generan después de compilar y van en Informes y en el paquete de pruebas; esta descripción del procedimiento no sustituye sus resultados.

El escritorio conserva versiones previas. Los archivos del celular se comparan por SHA-256. Drive permanece privado: se comprueban nombre, tamaño, carpeta y permisos del propietario. Sus hashes indicados son los originales locales; no representan una descarga independiente de cada archivo desde Drive. El índice se entrega separado para evitar un archivo que pretenda incluir su propio hash.

## Evidencia histórica y límites

VALIDACION-BETA4.md conserva la revisión anterior, incluidas sus pruebas de 90 minutos sobre el código Python definitivo, 120 recreaciones Android, pruebas de red prolongadas y una incidencia de instrumentación recuperada. Son evidencia histórica; no se atribuyen esas horas al código nuevo de beta 5. Las pruebas de catálogo anteriores distinguen descubrimiento, apertura observada, ventana y movimiento. No se convierte cada entrada del catálogo en una aplicación completamente certificada.

Siguen pendientes datos móviles reales porque no había saldo, otra PC o laptop física, ARM64, diferentes fabricantes, conexión física de monitores durante sesión y cambios reales de DPI. Tailscale necesita internet en ambos equipos, sesión iniciada y receptor disponible; no se demostró control desde otra red móvil ni despertar remoto. No se probaron apagados, suspensión, bloqueo ni reinicios reales durante el trabajo desatendido. No hay garantía de ausencia total de errores ni conmutación automática verificada entre asistentes de IA.

Si el disco deja de aceptar cualquier escritura, tampoco puede garantizarse guardar un informe nuevo. Las acciones ya enviadas a Windows no se deshacen al cancelar. Un fallo del reparador puede mantener el enfriamiento de un minuto; evita repetirlo en bucle y revisa el mensaje. La supervisión normal puede intentar recuperar un receptor que perdió salud aunque la petición explícita de reparación haya fallado.
