import sys,time,json,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion.core import Deck,start,atomic_json
root=Path(__file__).resolve().parents[1]
data=root/'.build/v2-test-data';deck=Deck(data,root,dry_run=True)
start(deck,local_port=48089,port=48090,bind='127.0.0.1');deck.refresh();deck.renew_pin()
atomic_json(data/'test-runtime.json',{'localToken':deck.local_token,'localPort':deck.local_port,'port':deck.port,'pid':os.getpid()})
while True:time.sleep(1)
