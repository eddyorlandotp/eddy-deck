from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from companion.installer import install_from
print('Instalación por usuario: '+str(install_from(root/'artifacts/windows/EddyDeck')))
