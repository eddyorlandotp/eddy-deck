# Pruebas por aplicación · Eddy Deck 2.1 Beta 1

Windows 11, 11 de septiembre de 2026. Inventario inicial: 149 entradas. Cada fila conserva el resultado más reciente; los JSON guardan también los errores iniciales y las repeticiones.

Una ventana observada puede ser un lanzador, acceso a cuenta o actualización. No demuestra que un juego esté listo ni que funcionen todas las funciones internas. Los cambios prueban derecha en modo ventana, izquierda maximizada, minimizar y restaurar a la derecha. Se respetan sesiones anteriores, permisos y diálogos; nunca se fuerza el cierre de otras apps.

Las aplicaciones de seguridad, cuenta, hardware, accesibilidad o superposición se registran como pendientes de recorrido manual. Las variantes de un lanzador compartido necesitan seleccionar su ventana exacta en Mi PC.

## Resultados registrados

- Prueba manual pendiente: sesión, hardware o permisos: 40.
- Abrió una ventana identificada: 71.
- Apertura enviada; ventana no identificada: 12.
- Lanzador compartido; selección manual pendiente: 9.
- Excluida: entrada inválida o herramienta del sistema: 14.
- Varias ventanas; requiere selección: 1.
- Ventana ya abierta; conservada: 2.

Cambios de ventana completos: 46. Parciales: 25.

Crear, editar, releer y eliminar un botón se comprobó por HTTP para todas las entradas del catálogo válido de esa ejecución (ver catalog-beta-crud.json). Eso es independiente de poder abrir o mover la aplicación.

## Detalle

| Aplicación | Apertura | Ventana | Observaciones |
| --- | --- | --- | --- |
| Acceso por voz | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Access | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal; Prueba repetida después de corregir el adaptador |
| AIMP | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Among Us | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Apex Legends | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: start_protected_game.exe, steamwebhelper.exe, steamwebhelper.exe; No se cerró ninguna ventana |
| ARK: Survival Ascended | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Quedó ventana o diálogo; no se forzó; Prueba repetida después de corregir el adaptador |
| AudioConverter | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Balatro | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| balenaEtcher | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Blackmagic Proxy Generator Lite | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana; Prueba repetida después de corregir el adaptador |
| Blackmagic RAW Player | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Blackmagic RAW Speed Test | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Blender 5.0 | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Blood Strike | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: NVIDIA Overlay.exe; No se cerró ninguna ventana |
| Calculator | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Camera | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| CapCut | Abrió una ventana identificada | 4 cambios verificados | Quedó ventana o diálogo; no se forzó; Prueba repetida después de corregir el adaptador |
| Character Map | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| ChatGPT | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| ChatGPT Discreto | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Claude | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Click to Do | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Quedó ventana o diálogo; no se forzó |
| Cliente de Riot | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| Clock | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Configuración | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Counter-Strike 2 | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; minimized: La aplicación no aceptó el diseño. Prueba modo ventana desde la app; los juegos a pantalla completa pueden controlar su posición.; Quedó ventana o diálogo; no se forzó |
| DaVinci Control Panels | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| DaVinci Resolve | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| Delta Force | Apertura enviada; ventana no identificada | Sin prueba de movimiento | No se cerró ninguna ventana |
| Desktop Overlay Host | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Dev Home | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| dfrgui | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Discord | Varias ventanas; requiere selección | Sin prueba de movimiento | Cerradas u ocultas tras cierre normal |
| EVE Online | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Ventanas adicionales: Discord.exe; Cierre normal confirmado |
| Excel | Abrió una ventana identificada | 4 cambios verificados | Quedó ventana o diálogo; no se forzó |
| ExitLag | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Explorador de archivos | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Fairlight Studio Utility | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Fallout 76 | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Feedback Hub | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| FL Cloud Plugins | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| FL Studio 2025 | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Fortnite | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Ventanas adicionales: opera.exe; Cierre normal confirmado |
| Forza Horizon 6 | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Quedó ventana o diálogo; no se forzó |
| Freddy Fazbear's Pizzeria Simulator | Abrió una ventana identificada | Cambios parcialmente compatibles | windowed: La aplicación cerró la ventana durante el movimiento.; maximized: Esa ventana ya cambió o se cerró. Actualiza la lista y selecciónala otra vez.; minimized: Esa ventana ya cambió o se cerró. Actualiza la lista y selecciónala otra vez.; windowed: Esa ventana ya cambió o se cerró. Actualiza la lista y selecciónala otra vez.; Ventanas adicionales: Pizzeria Simulator.exe; No se cerró ninguna ventana |
| Game Bar | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| GCC | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Get Help | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| GIGABYTE Control Center | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Gigabyte Dynamic Light | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Git GUI | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado; Prueba repetida después de corregir el adaptador |
| Grabación de acciones de usuario | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Halo Infinite | Apertura enviada; ventana no identificada | Sin prueba de movimiento | No se cerró ninguna ventana |
| Halo: Campaign Evolved | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; minimized: La aplicación no aceptó el diseño. Prueba modo ventana desde la app; los juegos a pantalla completa pueden controlar su posición.; Ventanas adicionales: HaloInfinite.exe; Cierre normal confirmado |
| Hollow Knight | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Hollow Knight: Silksong | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| HoYoPlay | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| HP Smart | Abrió una ventana identificada | 4 cambios verificados | Quedó ventana o diálogo; no se forzó |
| Información del sistema | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Inkscape | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; minimized: La aplicación no aceptó el diseño. Prueba modo ventana desde la app; los juegos a pantalla completa pueden controlar su posición.; Cierre normal confirmado |
| Inkview | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Introducción | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Iriun Webcam | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| LiveCaptions | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Lossless Scaling | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Lupa | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Magnify | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Mapa de caracteres | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Marvel Rivals | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: steamwebhelper.exe; No se cerró ninguna ventana |
| MateEngine | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Mecha BREAK | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: steamwebhelper.exe; No se cerró ninguna ventana |
| Medal | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Media Player | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Microsoft 365 Copilot | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Oculta tras cierre normal |
| Microsoft Clipchamp | Abrió una ventana identificada | 4 cambios verificados | Ventanas adicionales: msedgewebview2.exe; Cierre normal confirmado |
| Microsoft Edge | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Microsoft News | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Microsoft Store | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Microsoft Teams | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Microsoft To Do | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: ms-teams.exe; No se cerró ninguna ventana |
| Minecraft for Windows | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Minecraft Launcher | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Quedó ventana o diálogo; no se forzó |
| More... | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| MSI Afterburner | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Narrador | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Narrator | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Navegador Opera GX | Ventana ya abierta; conservada | Sin prueba de movimiento | No se cerró ninguna ventana |
| Notepad | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Notion | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| NVIDIA App | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| NVIDIA Control Panel | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| OBS Studio | Abrió una ventana identificada | 4 cambios verificados | Quedó ventana o diálogo; no se forzó |
| Ollama | Abrió una ventana identificada | 4 cambios verificados | Ventanas adicionales: WindowsTerminal.exe; Cierre normal confirmado |
| On-Screen Keyboard | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| OneDrive | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| OneNote | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| OP Auto Clicker | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Outlook | Abrió una ventana identificada | 4 cambios verificados | Quedó ventana o diálogo; no se forzó |
| Outlook (classic) | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Ventanas adicionales: OUTLOOK.EXE; Cierre normal confirmado |
| Paint | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Panel de control | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Phone Link | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Photos | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Power Automate | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| PowerPoint | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Publisher | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Razer Synapse | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Realtek Audio Console | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Resource Monitor | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Riot Client | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| RivaTuner Statistics Server | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Roblox | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Roblox Player | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Oculta tras cierre normal |
| Roblox Studio | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: RobloxStudioInstaller.exe; No se cerró ninguna ventana |
| Rufus | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Snipping Tool | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Solitaire & Casual Games | Abrió una ventana identificada | 4 cambios verificados | Ventanas adicionales: RobloxStudioBeta.exe; Oculta tras cierre normal |
| Sound Recorder | Abrió una ventana identificada | 4 cambios verificados | Ventanas adicionales: RobloxStudioBeta.exe; Cierre normal confirmado |
| STALZONE | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Stardew Valley | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Steam | Ventana ya abierta; conservada | Sin prueba de movimiento | No se cerró ninguna ventana |
| SteelSeries GG | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Steps Recorder | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Sticky Notes | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Sticky Notes (new) | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| Subtítulos en directo | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| System Information | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| TagEditor | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Tailscale | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Task Manager | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Teclado en pantalla | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| TIDAL | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Tor Browser | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Totally Accurate Battle Simulator | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| VALORANT | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |
| Visor de eventos | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| Visual Studio Code | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| VoiceAccess | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| Wallpaper Engine | Prueba manual pendiente: sesión, hardware o permisos | Sin prueba de movimiento | No se cerró ninguna ventana |
| War Thunder | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Cierre normal confirmado |
| Weather | Abrió una ventana identificada | 4 cambios verificados | Cierre normal confirmado |
| Website | Excluida: entrada inválida o herramienta del sistema | Sin prueba de movimiento | No se cerró ninguna ventana |
| WhatsApp | Apertura enviada; ventana no identificada | Sin prueba de movimiento | No se cerró ninguna ventana |
| Windows Media Player Legacy | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: setup_wm.exe; No se cerró ninguna ventana |
| Word | Abrió una ventana identificada | 4 cambios verificados | Oculta tras cierre normal |
| Wuthering Waves | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: steamwebhelper.exe; No se cerró ninguna ventana |
| XBOX | Apertura enviada; ventana no identificada | Sin prueba de movimiento | Ventanas adicionales: ApplicationFrameHost.exe; No se cerró ninguna ventana |
| YandereSimulator - Acceso directo | Abrió una ventana identificada | Cambios parcialmente compatibles | maximized: Esta ventana tiene tamaño fijo. Usa modo ventana para moverla entre pantallas.; Oculta tras cierre normal |
| Zenless Zone Zero | Lanzador compartido; selección manual pendiente | Sin prueba de movimiento | No se cerró ninguna ventana |

Los cierres adicionales verificados después de una pausa se registran en catalog-beta-cleanup-tests.jsonl cuando están disponibles. Una apertura tardía o una ventana de identidad ambigua se conserva para revisión local.
