const fs=require('fs'),path=require('path'),vm=require('vm');
const root=process.cwd();
const ts=require(path.join(root,'node_modules/typescript'));
const React=require(path.join(root,'node_modules/react'));
const {renderToStaticMarkup}=require(path.join(root,'node_modules/react-dom/server'));
const base=JSON.parse(fs.readFileSync('src/fixtures/state.json','utf8'));
const rows=[];
function render(state,error=null){
 const cache={};
 function load(file){
  if(cache[file]) return cache[file];
  const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{target:ts.ScriptTarget.ES2020,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
  const exports={}; cache[file]=exports;
  function req(p){
   if(p.endsWith('/useHandoffState')||p==='./useHandoffState')return {useHandoffState:()=>({state,error})};
   if(p==='../api'||p==='./api') return {API_MODE:'live'};
   if(!p.startsWith('.')) return require(path.join(root,'node_modules',p));
   let target=path.resolve(path.dirname(file),p);
   if(!path.extname(target))target+=fs.existsSync(target+'.tsx')?'.tsx':'.ts';
   if(target.endsWith('.json'))return JSON.parse(fs.readFileSync(target,'utf8'));
   return load(target);
  }
  vm.runInNewContext(code,{exports,require:req,console,setInterval,clearInterval,setTimeout,clearTimeout});
  return exports;
 }
 return renderToStaticMarkup(React.createElement(load(path.join(root,'src/App.tsx')).default));
}
function check(name,fn){try{if(!fn())throw Error('Expected text was absent');rows.push([name,'PASS']);}catch(e){rows.push([name,'FAIL',e.message]);}}
check('Prototype identity visible',()=>render(base).includes('Prototype demo'));
check('Loading state visible',()=>render(null).includes('Loading'));
check('Backend outage banner visible',()=>render(null,'synthetic offline').includes('Backend unreachable'));
const empty={...base,incidents:[],critical_alerts:[],supervisor_queue:[],alerts:[],departments:[]};
check('Empty queue message visible',()=>render(empty).includes('No open incidents'));
check('Department alert rendered',()=>render(base).includes('accepted 0 of 12'));
const critical={...base,supervisor_queue:[],alerts:[],critical_alerts:[{incident_id:1,title:'CRITICAL CASE',quote:'UNIQUE CRITICAL EVIDENCE',reason:'REQUIRES REVIEW',evidence:['callback:1'],since:base.now,accepted:true,owner:'Demo operator'}],incidents:base.incidents.map(i=>({...i,accepted:true,critical:true,why:'Accepted by Demo operator'}))};
check('Accepted critical alert evidence remains visible outside top ten',()=>render(critical).includes('UNIQUE CRITICAL EVIDENCE'));
const many={...critical,critical_alerts:Array.from({length:12},(_,n)=>({...critical.critical_alerts[0],incident_id:n+1,quote:`PINNED-EVIDENCE-${n+1}-END`}))};
check('All twelve critical alerts render beyond the queue cap',()=>{
 const html=render(many);
 return many.critical_alerts.every(a=>html.includes(a.quote));
});
check('Critical lane absent when there are no alerts',()=>!render(empty).includes('Persistent critical alerts'));
for(const [accepted,acknowledged,label] of [
 [false,false,'Assigned · awaiting acknowledgment'],
 [false,true,'Acknowledged · awaiting acceptance'],
 [true,true,'Accepted'],
]) {
 check(`Ownership label: ${label}`,()=>{
  const html=render({...empty,incidents:[{...base.incidents[0],accepted,acknowledged}]});
  return html.includes(label);
 });
}
// Exit nonzero so an absent critical alert cannot be mistaken for a passing check.
process.exitCode=rows.some(row=>row[1]==='FAIL')?1:0;
console.log(JSON.stringify(rows,null,2));
