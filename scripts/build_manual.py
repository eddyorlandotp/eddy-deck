"""Create the same offline user manual for desktop, Android, and the in-app dialog."""
import html,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def inline(s):return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',html.escape(s))
def main():
 from companion.core import VERSION
 rows=[];opened=None
 for line in (ROOT/'docs/MANUAL-USUARIO.md').read_text(encoding='utf-8').splitlines():
  bullet=line.startswith('- ');number=re.match(r'^\d+\. (.*)',line)
  kind='ul' if bullet else 'ol' if number else None
  if opened!=kind:
   if opened:rows.append('</'+opened+'>')
   if kind:rows.append('<'+kind+'>')
   opened=kind
  if kind:rows.append('<li>'+inline(line[2:] if bullet else number[1])+'</li>')
  elif line.startswith('# '):rows.append('<h1>'+inline(line[2:])+'</h1>')
  elif line.startswith('## '):rows.append('<h2>'+inline(line[3:])+'</h2>')
  elif line.strip():rows.append('<p>'+inline(line)+'</p>')
 if opened:rows.append('</'+opened+'>')
 body='<article class="user-manual">'+''.join(rows)+'</article>'
 document='<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Eddy Deck · Manual de usuario</title><style>body{font:17px/1.65 system-ui,sans-serif;background:#f7f5ef;color:#252728;margin:0;padding:24px}article{max-width:820px;margin:auto;background:white;padding:clamp(20px,5vw,64px);border-radius:24px}h1{font-size:clamp(28px,5vw,44px);line-height:1.15}h2{margin-top:2em;font-size:24px;color:#344c48}li{margin:10px 0}strong{font-weight:650}@media print{body{padding:0;background:white}article{padding:0}h2{break-after:avoid}}</style>'+body+'</html>'
 (ROOT/'docs/MANUAL-USUARIO.html').write_text(document,encoding='utf-8')
 (ROOT/'ui/manual.js').write_text('const EDDY_CLIENT_VERSION='+json.dumps(VERSION)+';\nconst EDDY_MANUAL='+json.dumps(body,ensure_ascii=False)+';\n',encoding='utf-8')
 print('Manual HTML y versión integrada generados.')
if __name__=='__main__':main()
