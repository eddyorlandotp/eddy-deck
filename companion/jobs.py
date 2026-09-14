"""Durable receipts and one bounded, cancellable queue for window/routine work.

After a process interruption, work is marked interrupted, never replayed blindly.
This is at-most-once submission, not a claim of transactional Windows side effects.
"""
import collections, copy, hashlib, json, logging, sqlite3, threading, time, uuid
from contextlib import contextmanager
from pathlib import Path

class ReceiptError(Exception):
    def __init__(self,status,message): self.status=status; super().__init__(message)

class Journal:
    def __init__(self,folder):
        self.path=Path(folder)/'operations.sqlite3'; self.lock=threading.RLock();self.rate_times={}
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS receipts (device TEXT, id TEXT, digest TEXT, result TEXT, status INTEGER, at REAL, PRIMARY KEY(device,id))')
            db.execute('CREATE INDEX IF NOT EXISTS receipts_device_at ON receipts(device,at)')
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, device TEXT, data TEXT, at REAL)')
            db.execute('UPDATE receipts SET status=409,result=? WHERE result IS NULL', (json.dumps({'error':'La operación se interrumpió. Revisa el resultado en Windows antes de volver a enviarla.'}),))
            for jid,data in db.execute('SELECT id,data FROM jobs').fetchall():
                job=json.loads(data)
                if job['status'] in ('queued','running'):
                    job.update(status='interrupted',message='Windows o Eddy Deck se cerró. La rutina no se reanuda automáticamente.')
                    db.execute('UPDATE jobs SET data=? WHERE id=?',(json.dumps(job),jid))
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=8)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:yield db
        finally:db.close()
    def invoke(self,path,body,device,work):
        rid=body.get('requestId')
        if not isinstance(rid,str) or not 8<=len(rid)<=80: raise ReceiptError(400,'Falta el identificador de la acción.')
        digest=hashlib.sha256(json.dumps([path,body],sort_keys=True).encode()).hexdigest()
        with self.lock, self.connect() as db:
            row=db.execute('SELECT digest,result,status FROM receipts WHERE device=? AND id=?',(device,rid)).fetchone()
            if row:
                if row[0]!=digest: raise ReceiptError(409,'Ese identificador ya pertenece a otra acción.')
                if row[1] is None: raise ReceiptError(409,'La orden está en curso. Consulta Actividad antes de repetirla.')
                result=json.loads(row[1])
                if row[2]>=400: raise ReceiptError(row[2],result['error'])
                return result
            # Bounded rate per paired device; never prune receipts and accidentally
            # make old physical commands executable again.
            now=time.monotonic()
            if device not in self.rate_times:
                # Reconstruct at most one minute on restart. A past wall-clock
                # correction can make receipts appear future-dated; conservatively
                # count them now, but never block this process for hours or days.
                wall=time.time()
                recent=db.execute('SELECT at FROM receipts WHERE device=? ORDER BY at DESC LIMIT 180',(device,)).fetchall()
                self.rate_times[device]=collections.deque(now-max(0,wall-r[0]) for r in reversed(recent))
            recent=self.rate_times[device]
            while recent and now-recent[0]>=60:recent.popleft()
            if len(recent)>=180:
                raise ReceiptError(429,'Demasiadas órdenes. Espera un minuto.')
            db.execute('INSERT INTO receipts VALUES(?,?,?,NULL,0,?)',(device,rid,digest,time.time()))
            recent.append(now)
        try: result=work(); status=200
        except Exception as exc:
            status=getattr(exc,'status',400 if isinstance(exc,(ValueError,TypeError,KeyError)) else 500)
            result={'error':str(exc) or 'No se pudo completar la orden.'}
            with self.lock, self.connect() as db: db.execute('UPDATE receipts SET result=?,status=? WHERE device=? AND id=?',(json.dumps(result),status,device,rid))
            raise
        with self.lock, self.connect() as db: db.execute('UPDATE receipts SET result=?,status=? WHERE device=? AND id=?',(json.dumps(result),status,device,rid))
        return result
    def save_job(self,job):
        with self.lock, self.connect() as db:
            db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?,?)',(job['id'],job['device'],json.dumps(job),job['at']))
            db.execute('DELETE FROM jobs WHERE id IN (SELECT id FROM jobs ORDER BY at DESC LIMIT -1 OFFSET 200)')
    def jobs(self):
        with self.lock,self.connect() as db:return [json.loads(r[0]) for r in db.execute('SELECT data FROM jobs ORDER BY at DESC LIMIT 30')]
    def receipt(self,device,rid):
        with self.lock,self.connect() as db:
            row=db.execute('SELECT result,status FROM receipts WHERE device=? AND id=?',(device,rid)).fetchone()
        if not row:return {'status':'notReceived'}
        if row[0] is None:return {'status':'inProgress'}
        return {'status':'failed' if row[1]>=400 else 'received','result':json.loads(row[0])}

class Cancelled(Exception): pass

class Queue:
    def __init__(self,journal,execute,event,authorized):
        self.journal=journal;self.execute=execute;self.event=event;self.authorized=authorized
        self.condition=threading.Condition();self.waiting=[];self.active=None;self.stopped=False;self.paused=False;self.fatal_error=''
        self.thread=threading.Thread(target=self.run,daemon=True,name='EddyDeckActions');self.thread.start()
    def submit(self,name,steps,device,on_error='stop'):
        with self.condition:
            if self.stopped:raise ValueError('Eddy Deck se está cerrando.')
            if not self.thread.is_alive():raise ValueError('La cola se detuvo. Reinicia Eddy Deck y revisa Actividad antes de repetir una orden.')
            if len(self.waiting)>=20:raise ValueError('La cola está llena. Cancela alguna rutina o espera.')
            # Duplicate taps within a routine's entire pending lifetime don't queue
            # two identical routines, even when their request IDs differ.
            key=json.dumps([device,name,steps,on_error],sort_keys=True)
            for item in ([self.active] if self.active else [])+self.waiting:
                if item['key']==key and not item['cancel'].is_set():return {'status':'queued','jobId':item['job']['id'],'message':'Esa tarea ya está en la cola.'}
            job={'id':uuid.uuid4().hex,'device':device,'name':name,'at':time.time(),'status':'queued','message':'En cola','step':0,'total':len(steps),'results':[]}
            self.journal.save_job(job)
            self.waiting.append({'job':job,'steps':copy.deepcopy(steps),'cancel':threading.Event(),'key':key,'onError':on_error})
            self.condition.notify()
            return {'status':'queued','jobId':job['id'],'message':'En cola: '+name}
    def cancel(self,jid,device):
        with self.condition:
            for item in ([self.active] if self.active else [])+self.waiting:
                if item['job']['id']==jid:
                    if device!='local' and item['job']['device']!=device:raise ReceiptError(403,'Solo puedes cancelar tus propias tareas.')
                    item['cancel'].set()
                    if item in self.waiting:
                        item['job'].update(status='cancelled',message='Cancelada antes de empezar.');self.journal.save_job(item['job']);self.waiting.remove(item)
                        return {'status':'cancelled','message':'Tarea retirada de la cola.'}
                    return {'status':'cancelling','message':'Se cancelarán los pasos pendientes. Lo ya abierto permanece.'}
        return {'status':'finished','message':'La tarea ya terminó.'}
    def cancel_all(self):
        with self.condition:
            for item in ([self.active] if self.active else [])+self.waiting:item['cancel'].set()
            cancelled,self.waiting=self.waiting,[]
            failure=None
            for item in cancelled:
                item['job'].update(status='cancelled',message='Cancelada antes de empezar.')
                try:self.journal.save_job(item['job'])
                except Exception as exc:
                    failure=exc
                    logging.getLogger('eddydeck').exception('No se pudo guardar una cancelación')
            if failure:
                # All in-memory work is cancelled even if one durable write
                # fails. Reject new work; reopening marks unsaved jobs interrupted.
                self.stopped=True
                self.fatal_error='No se pudieron guardar las cancelaciones. Revisa el disco y repara Eddy Deck; no se repetirán las tareas pendientes.'
            self.condition.notify_all()
            if failure:raise ReceiptError(503,self.fatal_error) from failure
    def pause(self,enabled):
        with self.condition:
            self.paused=enabled;self.condition.notify_all()
        return {'status':'paused' if enabled else 'resumed','message':'La tarea actual termina; las siguientes esperan.' if enabled else 'La cola continúa.'}
    def status(self):
        with self.condition:return {'paused':self.paused,'waiting':len(self.waiting),'active':self.active['job']['id'] if self.active else None,'healthy':self.thread.is_alive() and not self.fatal_error,'error':self.fatal_error}
    def run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:(self.waiting and not self.paused) or self.stopped)
                if self.stopped:return
                item=self.waiting.pop(0);self.active=item
            job=item['job'];deadline=time.monotonic()+300
            def check():
                if self.stopped or item['cancel'].is_set():raise Cancelled('Cancelada; no se ejecutarán más pasos.')
                if not self.authorized(job['device']):raise Cancelled('Se revocó el celular que envió la tarea.')
                if time.monotonic()>deadline:raise Cancelled('Se alcanzó el límite de cinco minutos. Revisa la tarea.')
            failed=False
            try:
                check();job.update(status='running',message='En curso');self.journal.save_job(job)
                for i,step in enumerate(item['steps']):
                    check();job['step']=i+1;self.journal.save_job(job)
                    try: result=self.execute(step,check)
                    except Cancelled:raise
                    except Exception as exc:
                        failed=True;result={'status':'failed','message':str(exc)}
                        job['results'].append(result);self.journal.save_job(job)
                        if item['onError']=='stop':raise
                        continue
                    if result.get('status')=='needs_attention':failed=True
                    job['results'].append(result);self.journal.save_job(job)
                    check()  # Cancellation during the final effect must not become "completed".
                job.update(status='partial' if failed else 'completed',message='Terminó con avisos.' if failed else 'Completada.')
            except Cancelled as exc:job.update(status='cancelled',message=str(exc))
            except Exception as exc:job.update(status='failed',message=str(exc))
            finally:
                try:self.journal.save_job(job);self.event(job['name']+': '+job['message'])
                except Exception:
                    # Stop accepting work with an unreliable journal. Health
                    # exposes this to the supervisor; nothing is replayed.
                    self.fatal_error='No se pudo guardar el resultado de una tarea. Revisa el disco y repara Eddy Deck.'
                    logging.getLogger('eddydeck').exception('La cola perdió su registro duradero')
                finally:
                    with self.condition:self.active=None
                if self.fatal_error:return
    def close(self):
        with self.condition:
            self.stopped=True
            for item in self.waiting:
                item['cancel'].set()
                item['job'].update(status='cancelled',message='Eddy Deck se cerró antes de empezar.')
                try:self.journal.save_job(item['job'])
                except Exception:
                    # Disk failure cannot prevent waking the worker or releasing
                    # listeners. Recovery marks unsaved pending jobs interrupted.
                    self.fatal_error='No se pudo guardar la cancelación al cerrar. Revisa el disco; las tareas pendientes no se repetirán automáticamente.'
                    logging.getLogger('eddydeck').exception('No se pudo registrar la cancelación al cerrar')
            self.waiting.clear();self.condition.notify_all()
        self.thread.join(3)
