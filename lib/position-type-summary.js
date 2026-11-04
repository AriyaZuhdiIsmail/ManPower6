(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  else root.PositionTypeSummary=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const clean=v=>String(v==null?'':v).trim().replace(/\s+/g,' ');
  function label(v){
    const t=clean(v);
    if(!t||/^(tidak diketahui|unknown|n\/a|null|undefined)$/i.test(t))return 'Tidak Terklasifikasi';
    if(/^definitif$/i.test(t))return 'Definitif';
    if(/^penugasan$/i.test(t))return 'Penugasan';
    if(/^masa evaluasi$/i.test(t))return 'Masa Evaluasi';
    return t;
  }
  function build(rows,allRows,level){
    const source=Array.isArray(allRows)?allRows:(Array.isArray(rows)?rows:[]);
    const allTypes=[...new Set(source.map(r=>label(r.pt)))];
    const fixed=['Definitif','Penugasan','Masa Evaluasi'];
    const types=[...fixed.filter(x=>allTypes.includes(x)),...allTypes.filter(x=>!fixed.includes(x)&&x!=='Tidak Terklasifikasi').sort((a,b)=>a.localeCompare(b,'id')),...(allTypes.includes('Tidak Terklasifikasi')?['Tidak Terklasifikasi']:[])];
    const seen=new Set(),groups=new Map();
    (Array.isArray(rows)?rows:[]).forEach(r=>{
      const nik=clean(r.nik);if(!nik||seen.has(nik))return;seen.add(nik);
      const job=clean(r.job)||'-',role=clean(r.jn)||job||'Jabatan Tidak Teridentifikasi';
      const cab=level==='C'?clean(r.p&&r.p[2]):'',out=level==='C'?clean(r.p&&r.p[3]):'';
      const key=(level==='C'?[cab,out,job,role]:[job,role]).join('\u001f');
      const g=groups.get(key)||{cab,out,job,jn:role,total:0,byType:{}};
      const type=label(r.pt);g.total++;g.byType[type]=(g.byType[type]||0)+1;groups.set(key,g);
    });
    const result=[...groups.values()].sort((a,b)=>b.total-a.total||a.jn.localeCompare(b.jn,'id'));
    const reconciled=result.reduce((n,r)=>n+r.total,0);
    return {types,rows:result,uniqueEmployees:seen.size,reconciled,ok:reconciled===seen.size&&result.every(r=>types.reduce((n,t)=>n+(r.byType[t]||0),0)===r.total)};
  }
  return {label,build};
});
