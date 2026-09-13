// Execute the production API wrapper with deterministic transport gates.
// No actual PC commands, credentials, browser navigation or network requests.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'ui/extended.js'),'utf8');
function fixture(){
 const saved=new Map();let next=0;
 const c={native:true,bootstrap:{pcId:'fixture-A'},connectionEpoch:0,state:{protocolVersion:2},api:null,
  $:()=>null,toast:()=>{},requestId:()=>`fixture-request-${++next}`,JSON,Error,Object,Array,Number,
  localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)},
  nativeCall:()=>{throw Error('Unexpected native call')},AbortController,setTimeout,clearTimeout};
 vm.createContext(c);vm.runInContext(source.slice(source.indexOf('async function transport('),source.indexOf('let refreshTask=')),c);return {c,saved};
}
const checks=[];
(async()=>{
 for(const kind of ['direct-403','receipt-failed','receipt-network-failed']){
  const {c,saved}=fixture();let release,entered;const reached=new Promise(r=>entered=r),gate=new Promise(r=>release=r);let sends=0;
  c.transport=async(p,b,pc)=>{
   assert.equal(pc,'fixture-A');
   if(p==='/api/media'){sends++;if(kind!=='direct-403')throw Error('Reply lost');}
   entered();await gate;
   if(kind==='direct-403')throw Object.assign(Error('Old PC rejected'),{server:true,status:403});
   if(kind==='receipt-network-failed')throw Error('Old network unreachable');
   return {status:'failed',result:{error:'Old command failed'}};
  };
  const command=c.api('/api/media',{action:'toggle'});await reached;c.connectionEpoch++;c.bootstrap={pcId:'fixture-B'};release();
  await assert.rejects(command,/PC anterior/);assert.equal(sends,1);assert(!saved.has('eddy-pending-fixture-B'));
  checks.push('Changed PC rejects stale '+kind+' and does not change the new PC journal');
 }
 {
  const {c,saved}=fixture();let release,entered;const atReceipt=new Promise(r=>entered=r),gate=new Promise(r=>release=r);let effects=0;
  c.transport=async(p,b,pc)=>{assert.equal(pc,'fixture-A');if(p==='/api/media'){effects++;throw Error('Reply lost after effect');}entered();await gate;return {status:'received',result:{status:'old-PC-success'}};};
  const command=c.api('/api/media',{action:'toggle',target:'system'});await atReceipt;
  c.connectionEpoch++;c.bootstrap={pcId:'fixture-B'};release();
  let error;try{await command;}catch(e){error=e;}
  assert(error&&/PC anterior/.test(error.message),'Receipt arriving after PC switch must not report success on new PC');
  assert.equal(effects,1);assert(!saved.has('eddy-pending-fixture-B'));
  checks.push('Lost reply then PC switch during receipt query rejects stale success and never writes new PC storage');
 }
 {
  const {c}=fixture();let effects=0,id;
  c.transport=async(p,b,pc)=>{if(p==='/api/media'){effects++;id=b.requestId;throw Error('Reply lost');}assert.equal(b.id,id);return {status:'received',result:{status:'submitted'}};};
  assert.equal((await c.api('/api/media',{action:'toggle'})).status,'submitted');assert.equal(effects,1);
  checks.push('Lost reply reconciles one existing receipt without resending the physical action');
 }
 {
  const {c,saved}=fixture();let id;
  c.transport=async(p,b)=>{if(p==='/api/media')id=b.requestId;throw Error('All replies unavailable');};
  await assert.rejects(c.api('/api/media',{action:'toggle'}));
  const reopened=fixture();for(const [k,v] of saved)reopened.saved.set(k,v);
  reopened.c.transport=async(p,b)=>{assert.equal(b.requestId,id);return {status:'submitted'};};
  assert.equal((await reopened.c.api('/api/media',{action:'toggle'})).status,'submitted');
  assert.equal(Object.keys(JSON.parse(reopened.saved.get('eddy-pending-fixture-A'))).length,0);
  checks.push('Recreated JavaScript context retains the original request ID after transport and receipt both fail');
 }
 {
  const {c}=fixture();let sends=0;c.localStorage.setItem=()=>{throw Error('Quota exceeded')};c.transport=async()=>{sends++;};
  await assert.rejects(c.api('/api/media',{action:'toggle'}),/guardar la orden/);assert.equal(sends,0);
  checks.push('Storage failure prevents transmission before a command could become untracked');
 }
 fs.writeFileSync(path.join(root,'artifacts/beta5-ui-combined-tests.json'),JSON.stringify({passed:true,checks,count:checks.length,sourceSHA256:crypto.createHash('sha256').update(source).digest('hex'),scope:'Production API wrapper in isolated JavaScript VM with synthetic transport; not physical Android rotation or mobile-data test'},null,2));console.log(JSON.stringify({passed:true,count:checks.length}));
})().catch(e=>{console.error(e);process.exitCode=1});
