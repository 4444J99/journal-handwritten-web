import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {canonicalJSON} from '../studio/release-canonical.mjs';

test('numeric geometry and Unicode keys have identical Python/JS digest input bytes',()=>{
  const wire='{"integerFloat":1.0,"small":1e-7,"fraction":0.12345678901234568,"zero":-0.0,"array":[null,true,1e-6],"😀":"astral","\\ue000":"bmp"}';
  const python=spawnSync('python3',['-c','import sys,json;sys.path.insert(0,sys.argv[1]);from release_canonical import canonical;print(canonical(json.load(sys.stdin)),end="")',fileURLToPath(new URL('../tools',import.meta.url))],{input:wire,encoding:'utf8'});
  assert.equal(python.status,0,python.stderr);
  assert.equal(python.stdout,canonicalJSON(JSON.parse(wire)));
});
test('typed nodes prevent payload collisions and refuse lossy JSON forms',()=>{
  assert.notEqual(canonicalJSON(1),canonicalJSON(['number','3ff0000000000000']));
  assert.notEqual(canonicalJSON(true),canonicalJSON(1));
  assert.equal(canonicalJSON(-0),canonicalJSON(0));
  for(const bad of [NaN,Infinity,undefined,new Date(),9007199254740992,'\ud800',[,1]])assert.throws(()=>canonicalJSON(bad));
  const cyclic={};cyclic.self=cyclic;assert.throws(()=>canonicalJSON(cyclic),/Cyclic/);
  const hidden={};Object.defineProperty(hidden,'hidden',{value:1});
  const sparse=Array(1);sparse.extra=1;
  const symbol={[Symbol('private')]:1};
  for(const bad of [hidden,sparse,symbol,{get computed(){throw new Error('must not execute getter');}}])assert.throws(()=>canonicalJSON(bad),/Hidden|Extended/);
});
