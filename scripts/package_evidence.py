"""Bundle completed release evidence separately from binaries and private state."""
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from companion.core import VERSION

def product_sources():
    paths=list((ROOT/'companion').glob('*.py'))+list((ROOT/'android/src').rglob('*.java'))
    paths += [ROOT/'run.py',ROOT/'installer/Compatibility.cs',ROOT/'installer/GitHubUpdate.cs',ROOT/'android/AndroidManifest.xml',ROOT/'android/res/values/styles.xml',*list((ROOT/'companion').glob('*.cs'))]+[ROOT/'ui'/name for name in ('app.js','extended.js','beta2.js','pickers.js','styles.css','index.html')]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def validate_beta5(out):
    def report(name):return json.loads((out/name).read_text(encoding='utf-8-sig'))
    campaign=report('beta5-daily-campaign.json')
    if not campaign.get('passed') or campaign.get('cycles',0)<30 or campaign.get('testsRun',0)<300 or campaign.get('failures') or campaign.get('sourceHashes')!=product_sources() or campaign.get('sourceChangedDuringRun'):
        raise RuntimeError('La campaña activa beta5 está incompleta, falló o corresponde a otro código.')
    core=report('beta5-core-tests.json')
    if not core.get('passed') or core.get('testsRun',0)<156 or core.get('sourceHashes')!=product_sources():raise RuntimeError('Falta la regresión Python del código actual.')
    ui=report('beta5-ui-combined-tests.json')
    if not ui.get('passed') or ui.get('count',0)<7 or ui.get('sourceSHA256')!=product_sources()[str(Path('ui')/'extended.js')]:raise RuntimeError('Falta la regresión de respuestas atrasadas.')
    observed=report('beta5-postinstall-observation.json')
    if observed.get('status')!='completed' or observed.get('elapsedSeconds',0)<90 or observed.get('samplesWithIssues') or not observed.get('samples') or any(s.get('version')!=VERSION for s in observed['samples']):raise RuntimeError('Falta comprobar la instalación beta5 sin incidencias.')
    android=report('beta5-android-installed-tests.json')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<56:raise RuntimeError('Falta comprobar el APK instalado actual.')
    release=report('beta5-release-verification.json');phone=report('beta5-final-device-verification.json')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate')):raise RuntimeError('Falta verificar el paquete y su instalación.')
    if phone.get('version')!=VERSION or not all(phone.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan las copias verificadas del teléfono.')

def validate_beta6(out):
    def report(name):return json.loads((out/('beta6-'+name+'.json')).read_text(encoding='utf-8-sig'))
    core=report('core-tests');live=report('tidal-live-tests');ui=report('tidal-ui-tests');phone=report('tidal-phone-tests')
    if not core.get('passed') or core.get('testsRun',0)<175 or core.get('sourceHashes')!=product_sources():raise RuntimeError('Falta la regresión actual de beta6.')
    if not live.get('passed') or live.get('count',0)<12 or live.get('sourceHashes')!=product_sources():raise RuntimeError('Falta comprobar TIDAL real con el código actual.')
    if not ui.get('passed') or ui.get('count',0)<8 or ui.get('sourceHashes')!=product_sources():raise RuntimeError('Falta comprobar los controles de música actuales.')
    if not phone.get('passed') or phone.get('version')!=VERSION or not all(phone.get(k) for k in ('homePaused','musicAutoPaused','musicDirectPaused','timelineStopped','installedHelperMatches')):raise RuntimeError('Falta comprobar la pausa desde el celular instalado.')
    android=report('android-installed-tests')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<56:raise RuntimeError('Falta la regresión Android instalada.')
    release=report('release-verification');copies=report('final-device-verification')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate','tidalHelperSignedAndInstalled')):raise RuntimeError('Falta verificar la instalación Windows actual.')
    if copies.get('version')!=VERSION or not all(copies.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan las copias del teléfono.')

def validate_beta7(out):
    def report(name):return json.loads((out/('beta7-'+name+'.json')).read_text(encoding='utf-8-sig'))
    for name,minimum in [('core-tests',187),('media-audit-live',22),('visible-ui-tests',18)]:
        item=report(name)
        if not item.get('passed') or item.get('testsRun',item.get('count',0))<minimum or item.get('sourceHashes')!=product_sources():raise RuntimeError('Falta evidencia del código actual: '+name)
    volume=report('system-volume-live')
    if volume.get('status')!='passed' or not all(volume.get(k) for k in ('muteOnObserved','muteOffObserved','initialLevelAndMuteRestored','downObserved','upObserved')):raise RuntimeError('Falta comprobar volumen y silencio reales.')
    phone=report('phone-visible-tests')
    if phone.get('version')!=VERSION or not phone.get('passed') or not all(phone.get(k) for k in ('tidalPaused','aimpPaused','mediaPlayerPaused','helpersMatch','exportsVerified')):raise RuntimeError('Faltan controles visibles del Samsung instalado.')
    if phone.get('installedApkSHA256')!=hashlib.sha256((out/'EddyDeck-Android.apk').read_bytes()).hexdigest():raise RuntimeError('La prueba visible no corresponde al APK final.')
    android=report('android-installed-tests')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<58:raise RuntimeError('Falta instrumentación Android actual.')
    release=report('release-verification');copies=report('final-device-verification')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate','tidalHelperSignedAndInstalled','mediaHelperSignedAndInstalled')):raise RuntimeError('Falta comprobar instalación Windows actual.')
    if copies.get('version')!=VERSION or not all(copies.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan copias verificadas del teléfono.')

def validate_beta8(out):
    def report(name):return json.loads((out/('beta8-'+name+'.json')).read_text(encoding='utf-8-sig'))
    for name,minimum in [('core-tests',190),('visual-tests',53),('media-ui-tests',24)]:
        item=report(name)
        if not item.get('passed') or item.get('testsRun',item.get('count',0))<minimum or item.get('sourceHashes')!=product_sources():raise RuntimeError('Falta evidencia actual de beta8: '+name)
    design=report('design-checks')
    if not design.get('passed') or design.get('sourceHashes')!=product_sources():raise RuntimeError('Falta verificar contraste y alcance del diseño.')
    phone=report('phone-design-tests')
    if not phone.get('passed') or phone.get('version')!=VERSION or not all(phone.get(k) for k in ('pickerObserved','backPreservesForm','searchObserved','draftPreserved','profilePreserved')):raise RuntimeError('Falta probar los menús en el Samsung.')
    if phone.get('installedApkSHA256')!=hashlib.sha256((out/'EddyDeck-Android.apk').read_bytes()).hexdigest():raise RuntimeError('La prueba visual no corresponde al APK final.')
    android=report('android-installed-tests')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<58:raise RuntimeError('Falta instrumentación Android actual.')
    release=report('release-verification');copies=report('final-device-verification')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate','tidalHelperSignedAndInstalled','mediaHelperSignedAndInstalled')):raise RuntimeError('Falta comprobar instalación Windows actual.')
    if copies.get('version')!=VERSION or not all(copies.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan copias verificadas del teléfono.')

def validate_beta9(out):
    def report(name):return json.loads((out/('beta9-'+name+'.json')).read_text(encoding='utf-8-sig'))
    for name,minimum in [('core-tests',209),('visual-tests',55),('media-ui-tests',24),('offline-ui-tests',4)]:
        item=report(name)
        if not item.get('passed') or item.get('testsRun',item.get('count',0))<minimum or item.get('sourceHashes')!=product_sources():raise RuntimeError('Falta evidencia actual beta9: '+name)
    live=report('live-reconnection')
    if not live.get('passed') or live.get('version')!=VERSION or live.get('sourceHashes')!=product_sources():raise RuntimeError('Falta reconexión instalada actual.')
    for key in ('originalIdentityPreserved','canonicalPhysicalStorage','lanConnected','vpnConnected','receiverColdStartReconnected','originalProfilePreserved'):
        if not live.get(key):raise RuntimeError('Falta caso de reconexión: '+key)
    if live.get('installedApkSHA256')!=hashlib.sha256((out/'EddyDeck-Android.apk').read_bytes()).hexdigest():raise RuntimeError('La reconexión no corresponde al APK final.')
    android=report('android-installed-tests')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<62:raise RuntimeError('Falta instrumentación Android actual beta9.')
    release=report('release-verification');copies=report('final-device-verification')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate')):raise RuntimeError('Falta instalación verificada beta9.')
    if copies.get('version')!=VERSION or not all(copies.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan copias verificadas beta9.')

def validate_beta10(out):
    def report(name):return json.loads((out/('beta10-'+name+'.json')).read_text(encoding='utf-8-sig'))
    for name,minimum in [('core-tests',224),('launch-ui',15),('visual-tests',55),('launch-live',10)]:
        item=report(name)
        if not item.get('passed') or item.get('testsRun',item.get('count',0))<minimum or item.get('sourceHashes')!=product_sources():raise RuntimeError('Falta evidencia actual beta10: '+name)
    if not report('launch-live').get('originalProfileUnchanged'):raise RuntimeError('La rutina original no quedó preservada en las pruebas.')
    android=report('android-installed-tests')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('cycles',0)<3 or android.get('checks',0)<24 or android.get('basicAssertions',0)<63:raise RuntimeError('Falta instrumentación Android actual beta10.')
    release=report('release-verification');copies=report('final-device-verification');phone=report('phone-launch-tests')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate')):raise RuntimeError('Falta verificar instalación beta10.')
    if copies.get('version')!=VERSION or not all(copies.get(k) for k in ('installedApkMatches','phoneWindowsInstallerMatches','phoneDocumentationMatches')):raise RuntimeError('Faltan copias verificadas beta10.')
    if not phone.get('passed') or phone.get('version')!=VERSION or phone.get('installedApkSHA256')!=hashlib.sha256((out/'EddyDeck-Android.apk').read_bytes()).hexdigest():raise RuntimeError('Falta comprobar el menú en el Android instalado.')

def validate_beta11(out):
    def report(name):
        try:return json.loads((out/('beta11-'+name+'.json')).read_text(encoding='utf-8-sig'))
        except (OSError,ValueError):raise RuntimeError('Falta un informe válido de beta11: '+name) from None
    for name,minimum in [('core-tests',244),('visual-tests',55),('pickers-tests',31)]:
        item=report(name)
        if not item.get('passed') or item.get('testsRun',item.get('count',0))<minimum or item.get('sourceHashes')!=product_sources():raise RuntimeError('Falta regresión actual beta11: '+name)
    updater=report('updater-tests')
    if not updater.get('passed') or updater.get('count',0)<49 or updater.get('sourceSHA256')!=hashlib.sha256((ROOT/'installer/GitHubUpdate.cs').read_bytes()).hexdigest():raise RuntimeError('Falta probar el actualizador C# actual.')
    http=report('http-tests');monitor=report('monitor-tests');catalog=report('catalog-live')
    if http.get('failures') or http.get('count',0)<90 or not monitor.get('passed') or monitor.get('topologies',0)<1000:raise RuntimeError('Falta matriz HTTP/monitores.')
    if len(catalog['rows'])!=catalog['catalogCount'] or len({r['id'] for r in catalog['rows']})!=catalog['catalogCount']:raise RuntimeError('Hay entradas del catálogo sin clasificar.')
    phone=report('phone-walkthrough');apk=hashlib.sha256((out/'EddyDeck-Android.apk').read_bytes()).hexdigest()
    equivalent=phone.get('finalBuildEquivalence',{})
    current_ui=phone.get('installedApkSHA256')==apk or (equivalent.get('passed') and equivalent.get('sameAndroidCodeResourcesAndUI') and equivalent.get('testedApkSHA256')==phone.get('installedApkSHA256') and equivalent.get('finalApkSHA256')==apk)
    final_phone=report('phone-launch-tests')
    if not phone.get('passed') or not current_ui or not phone.get('profilePreserved') or not final_phone.get('passed') or final_phone.get('installedApkSHA256')!=apk:raise RuntimeError('Falta recorrido físico del Samsung actual o equivalencia verificable de su interfaz.')
    media=report('media-audit-live');phone_media=report('phone-visible-tests')
    if not media.get('passed') or media.get('count',0)<21 or media.get('sourceHashes')!=product_sources():raise RuntimeError('Falta prueba real de los tres reproductores.')
    if not phone_media.get('passed') or phone_media.get('installedApkSHA256')!=apk or not all(phone_media.get(k) for k in ('tidalPaused','aimpPaused','mediaPlayerPaused','helpersMatch','exportsVerified')):raise RuntimeError('Faltan controles físicos de música del Samsung.')
    android=report('android-installed-tests');release=report('release-verification')
    if not android.get('passed') or android.get('installedVersion')!=VERSION or android.get('basicAssertions',0)<63 or android.get('checks',0)<24:raise RuntimeError('Falta regresión Android instalada.')
    if release.get('version')!=VERSION or not all(release.get(k) for k in ('releaseVerified','installedIntegrityVerified','profileAndPairingPreserved','phoneReconnectedAfterUpdate')):raise RuntimeError('Falta instalación beta11 verificada.')
    resolution=report('review-resolution')
    if resolution.get('rounds')!=1 or not resolution.get('readOnly') or not resolution.get('resolutions'):raise RuntimeError('Falta resolución de la revisión de Claude.')

def validate_completed(out):
    if VERSION=='2.2.9-beta.11':return validate_beta11(out)
    if VERSION=='2.2.8-beta.10':return validate_beta10(out)
    if VERSION=='2.2.7-beta.9':return validate_beta9(out)
    if VERSION=='2.2.6-beta.8':return validate_beta8(out)
    if VERSION=='2.2.5-beta.7':return validate_beta7(out)
    if VERSION=='2.2.4-beta.6':return validate_beta6(out)
    if VERSION=='2.2.3-beta.5':return validate_beta5(out)
    if VERSION!='2.2.2-beta.4':
        raise RuntimeError('Actualiza la matriz de evidencias para esta versión; no basta con informes de una beta anterior.')
    requirements={'beta2-soak-tests.json':7200,'beta2-soak-final-tests.json':4800,'beta2-background-tests.json':2400,'beta2-soak-final-source-tests.json':600}
    if VERSION=='2.2.2-beta.4':
        requirements.update({'beta3-resumed-soak-tests.json':9000,'beta4-soak-tests.json':7200,'beta4-soak-final-source-tests.json':5400,'beta4-installed-observation.json':8040,'beta4-network-soak-tests.json':1800,'beta4-postinstall-observation.json':90})
        requirements['beta4-concurrent-receipts-soak.json']=1800
    for name,minimum in requirements.items():
        data=json.loads((out/name).read_text(encoding='utf-8-sig'))
        if data.get('status') not in ('passed','completed') or data.get('elapsedSeconds',0)<minimum:
            raise RuntimeError('El ensayo no ha terminado su duración requerida: '+name)
        if data.get('unexpectedErrors') or data.get('failures'):
            raise RuntimeError('Revisa los errores del ensayo: '+name)
        if data.get('unplannedIssueSamples',0):
            if name!='beta4-installed-observation.json':raise RuntimeError('La observación final contiene incidencias: '+name)
            review=json.loads((out/'beta4-observation-incident-review.json').read_text(encoding='utf-8'))
            incidents=[s for s in data['samples'] if s['issues'] and not s['maintenance']]
            reviewed=review['incidents']
            if {s['atUTC'] for s in incidents}!={s['observedAtUTC'] for s in reviewed}:
                raise RuntimeError('Hay incidencias de observación sin revisar.')
            for item in reviewed:
                recovery=next((s for s in data['samples'] if s['atUTC']==item['recoveredAtUTC']),None)
                if item.get('resolution')!='recovered' or not recovery or recovery['issues']:
                    raise RuntimeError('Falta evidencia de recuperación de una incidencia.')
    if VERSION=='2.2.2-beta.4':
        final=json.loads((out/'beta4-soak-final-source-tests.json').read_text(encoding='utf-8'))
        if final.get('requestedSeconds',0)<5400:
            raise RuntimeError('El ensayo final debe solicitar al menos 5,400 segundos.')
        current={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'companion').glob('*.py')}
        if final.get('sourceHashes')!=current or final.get('sourceChangedDuringRun'):
            raise RuntimeError('El ensayo final no corresponde a las fuentes actuales.')
        lifecycle=json.loads((out/'beta4-lifecycle-soak-tests.json').read_text(encoding='utf-8'))
        if not lifecycle.get('passed') or lifecycle.get('cycles')!=120 or lifecycle.get('elapsedSeconds',0)<3570:
            raise RuntimeError('El ensayo de ciclo de vida Android no ha terminado.')

def main():
    out=ROOT/'artifacts'
    validate_completed(out)
    reports=[p for p in out.glob('beta*-*') if p.suffix in ('.json','.txt','.md') and not p.name.endswith('drive-verification.json')]
    reports.extend(p for p in out.glob('catalog-beta[0-9]*-*') if p.suffix in ('.json','.txt','.md','.csv'))
    manifest=[]
    target=out/f'EddyDeck-Pruebas-{VERSION}.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(set(reports)):
            raw=p.read_bytes();z.writestr('Informes/'+p.name,raw)
            manifest.append({'file':p.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        z.writestr('LEEME.txt','Informes de Eddy Deck '+VERSION+'. VALIDACION.md distingue hardware real, simulación y pendientes. Las salidas iniciales de pruebas no se convierten en aprobadas; consulta sus repeticiones y contexto. El índice de Drive se entrega por separado para evitar un archivo de verificación circular.\n')
        z.writestr('MANIFIESTO.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for entry in manifest:assert hashlib.sha256(z.read('Informes/'+entry['file'])).hexdigest()==entry['sha256']
    print(json.dumps({'file':target.name,'reports':len(manifest),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}))
if __name__=='__main__':main()
