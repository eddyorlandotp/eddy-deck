"""Summarize recorded outcomes without upgrading an observation to a pass."""
from pathlib import Path
import collections,json
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'artifacts'
original=json.loads((out/'catalog-beta-live.json').read_text(encoding='utf-8'))['rows']
latest={r['id']:r for r in original}
for file in sorted(out.glob('catalog-beta-retest*.json')):
    for r in json.loads(file.read_text(encoding='utf-8'))['rows']:latest[r['id']]=r
labels={
 'window_observed':'Abrió una ventana identificada',
 'existing_window_observed':'Ventana ya abierta; conservada',
 'excluded':'Excluida: entrada inválida o herramienta del sistema',
 'unavailable':'Instalación no verificada o acceso obsoleto',
 'submitted_no_identifiable_window':'Apertura enviada; ventana no identificada',
 'manual_session_hardware_or_permission_check':'Prueba manual pendiente: sesión, hardware o permisos',
 'shared_launcher_needs_manual_window_selection':'Lanzador compartido; selección manual pendiente',
 'multiple_windows_need_selection':'Varias ventanas; requiere selección',
 'same_target_as':'Mismo acceso que otra entrada',
 'failed':'Falló la apertura',
 'four_transitions_verified':'4 cambios verificados',
 'partial_transitions':'Cambios parcialmente compatibles',
 'not_tested':'Sin prueba de movimiento',
 'closed_test_window':'Cierre normal confirmado',
 'closed_or_hidden_test_windows':'Cerradas u ocultas tras cierre normal',
 'hidden_to_tray':'Oculta tras cierre normal',
 'window_or_prompt_remains':'Quedó ventana o diálogo; no se forzó',
 'not_needed':'No se cerró ninguna ventana',
}
def label(value):return labels.get(value,value)
counts=dict(collections.Counter(r['launch'] for r in latest.values()))
layouts=dict(collections.Counter(r['layout'] for r in latest.values()))
lines=['# Pruebas por aplicación · Eddy Deck 2.1 Beta 1','',
'Windows 11, 11 de septiembre de 2026. Inventario inicial: 149 entradas. Cada fila conserva el resultado más reciente; los JSON guardan también los errores iniciales y las repeticiones.','',
'Una ventana observada puede ser un lanzador, acceso a cuenta o actualización. No demuestra que un juego esté listo ni que funcionen todas las funciones internas. Los cambios prueban derecha en modo ventana, izquierda maximizada, minimizar y restaurar a la derecha. Se respetan sesiones anteriores, permisos y diálogos; nunca se fuerza el cierre de otras apps.','',
'Las aplicaciones de seguridad, cuenta, hardware, accesibilidad o superposición se registran como pendientes de recorrido manual. Las variantes de un lanzador compartido necesitan seleccionar su ventana exacta en Mi PC.','',
'## Resultados registrados','']
for key,value in counts.items():lines.append(f'- {label(key)}: {value}.')
lines+=['',f"Cambios de ventana completos: {layouts.get('four_transitions_verified',0)}. Parciales: {layouts.get('partial_transitions',0)}.",'',
'Crear, editar, releer y eliminar un botón se comprobó por HTTP para todas las entradas del catálogo válido de esa ejecución (ver catalog-beta-crud.json). Eso es independiente de poder abrir o mover la aplicación.','',
'## Detalle','', '| Aplicación | Apertura | Ventana | Observaciones |','| --- | --- | --- | --- |']
for prior in original:
    r=latest[prior['id']]
    details=[]
    if 'sameTarget' in r:details.append('Mismo destino: '+r['sameTarget'])
    for t in r.get('transitions',[]):
        if t['status']!='completed':details.append(t['mode']+': '+t.get('detail',t['status']))
    if r.get('detail'):details.append(r['detail'])
    if r.get('unidentifiedNewWindows'):details.append('Ventanas adicionales: '+', '.join(r['unidentifiedNewWindows']))
    details.append(label(r['cleanup']))
    if latest[r['id']] is not prior:details.append('Prueba repetida después de corregir el adaptador')
    cells=[r['name'],label(r['launch']),label(r['layout']),'; '.join(details)]
    lines.append('| '+' | '.join(x.replace('|','/').replace('\n',' ') for x in cells)+' |')
lines+=['','Los cierres adicionales verificados después de una pausa se registran en catalog-beta-cleanup-tests.jsonl cuando están disponibles. Una apertura tardía o una ventana de identidad ambigua se conserva para revisión local.','']
report='\n'.join(lines)
(out/'catalog-beta-summary.md').write_text(report,encoding='utf-8')
(ROOT/'docs/CATALOGO-PRUEBAS.md').write_text(report,encoding='utf-8')
print(json.dumps({'rows':len(latest),'launch':counts,'layout':layouts},ensure_ascii=False))
