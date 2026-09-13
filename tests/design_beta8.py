"""Read-only design/source checks; no live Windows controls."""
import hashlib,json,zipfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.package_evidence import product_sources
def luminance(h):
 c=[int(h[i:i+2],16)/255 for i in (1,3,5)];c=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in c];return sum(a*b for a,b in zip(c,[.2126,.7152,.0722]))
pairs=[('Unselected field','#5f7059','#ffffff'),('Primary action','#ffffff','#286b56'),('Body','#243330','#f6f7f5'),('Secondary text','#64736e','#f6f7f5'),('Field label','#4f6856','#f8faf7'),('Picker option','#3c553e','#fbfcf9'),('Selected option','#305335','#e6efdf'),('Dock active','#ffffff','#2d4836')]
contrast=[]
for name,fg,bg in pairs:
 a,b=sorted([luminance(fg),luminance(bg)]);ratio=(b+.05)/(a+.05);assert ratio>=4.5,(name,ratio);contrast.append({'name':name,'foreground':fg,'background':bg,'ratio':round(ratio,3),'passes4_5':True})
css=(ROOT/'ui/styles.css').read_text(encoding='utf-8');assert '@import' not in css and 'https://' not in css
baseline=Path.home()/'Desktop/Eddy Deck/Versiones/2.2.5-beta.7/EddyDeck-Codigo.zip'
with zipfile.ZipFile(baseline) as z:
 old=z.read('EddyDeck-Codigo/android/src/com/eddy/deck/MainActivity.java')
 expected=old.replace(b'Color.rgb(247,245,239)',b'Color.rgb(246,247,245)').replace(b'beta2\\\\.js|',b'beta2\\\\.js|pickers\\\\.js|')
 assert (ROOT/'android/src/com/eddy/deck/MainActivity.java').read_bytes().replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n')
 checked=[]
 for p in (ROOT/'companion').glob('*'):
  if p.suffix not in ('.py','.cs'):continue
  old=z.read('EddyDeck-Codigo/'+p.relative_to(ROOT).as_posix())
  if p.name=='core.py':old=old.replace(b"VERSION='2.2.5-beta.7'",b"VERSION='2.2.6-beta.8'").replace(b"'/beta2.js':'beta2.js',",b"'/beta2.js':'beta2.js','/pickers.js':'pickers.js',")
  assert p.read_bytes().replace(b'\r\n',b'\n')==old.replace(b'\r\n',b'\n'),p.name;checked.append(p.name)
report={'passed':True,'contrast':contrast,'localFontsOnly':True,'backendUnchangedExceptVersionAndStaticPickerRoute':checked,'androidActivityOnlyFourColorsAndLocalPickerPath':True,'sourceHashes':product_sources(),'scope':'Selected solid-color text/background pairs, not every pixel/overlay nor TalkBack certification. Comparison with delivered beta7 source with CRLF/LF normalized; Java changes limited to four colors and one local asset path.'}
(ROOT/'artifacts/beta8-design-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({'passed':True,'contrastPairs':len(contrast),'backendFilesChecked':len(checked),'androidFourColorsAndLocalPickerPathOnly':True}))
