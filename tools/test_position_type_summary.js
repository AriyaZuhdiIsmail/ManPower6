'use strict';
const assert = require('node:assert/strict');
const PT = require('../lib/position-type-summary.js');

const all = [
  {nik:'001', job:'AO', jn:'Account Officer', pt:'Definitif', p:['Area','A','Cabang 1','UPC A']},
  {nik:'002', job:'AO', jn:'Account Officer', pt:'Penugasan', p:['Area','A','Cabang 1','UPC A']},
  {nik:'003', job:'AO', jn:'Account Officer', pt:'Masa Evaluasi', p:['Area','A','Cabang 1','UPC A']},
  {nik:'004', job:'AO', jn:'Account Officer', pt:'Penugasan Khusus', p:['Area','A','Cabang 1','UPC A']},
  {nik:'005', job:'AO', jn:'Account Officer', pt:'', p:['Area','A','Cabang 1','UPC A']},
  // Deliberate duplicate NIK: it must never increment a second position-type count.
  {nik:'001', job:'SAO', jn:'Senior Account Officer', pt:'Penugasan', p:['Area','A','Cabang 1','UPC A']}
];
const result = PT.build(all, all, 'C');
assert.equal(result.ok, true);
assert.equal(result.uniqueEmployees, 5);
assert.equal(result.reconciled, 5);
assert.deepEqual(result.types, ['Definitif','Penugasan','Masa Evaluasi','Penugasan Khusus','Tidak Terklasifikasi']);
assert.equal(result.rows.length, 1);
assert.equal(result.rows[0].total, 5);
assert.equal(result.rows[0].byType.Definitif, 1);
assert.equal(result.rows[0].byType.Penugasan, 1);
assert.equal(result.rows[0].byType['Masa Evaluasi'], 1);
assert.equal(result.rows[0].byType['Penugasan Khusus'], 1);
assert.equal(result.rows[0].byType['Tidak Terklasifikasi'], 1);

const filtered = PT.build(all.filter(x => x.pt !== 'Definitif'), all, 'C');
assert.equal(filtered.reconciled, 5);
assert.ok(filtered.types.includes('Definitif')); // category remains available; zero in this filtered slice
assert.equal(filtered.rows[0].byType.Definitif || 0, 0);
console.log('PASS: Position Type dinamis, kategori baru, tidak terklasifikasi, deduplikasi NIK, dan rekonsiliasi total.');
