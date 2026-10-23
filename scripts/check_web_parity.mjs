import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import ts from '../site/node_modules/typescript/lib/typescript.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
let source=fs.readFileSync(path.join(root,'site/lib/gearmatch.ts'),'utf8');
source=source.replace(/import catalog from ['"]\.\/catalog\.json['"];?/, 'const catalog = '+fs.readFileSync(path.join(root,'data/catalog.json'),'utf8')+';');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
const temp=path.join(root,'site/.sites-runtime/parity.mjs');fs.mkdirSync(path.dirname(temp),{recursive:true});fs.writeFileSync(temp,compiled);
const {search}=await import(pathToFileURL(temp));
const gold=JSON.parse(fs.readFileSync(path.join(root,'evaluation/gold.json'),'utf8'));
const python=JSON.parse(fs.readFileSync(path.join(root,'evaluation/results.json'),'utf8')).systems.hybrid.cases;
const differences=[];
for(const row of gold){const got=search(row.query,row.filters,3).map(x=>x.product.id);const expected=python.find(x=>x.id===row.id).retrieved;if(JSON.stringify(got)!==JSON.stringify(expected))differences.push({id:row.id,python:expected,web:got});}
const report={cases:gold.length,identical_rankings:gold.length-differences.length,differences};
fs.writeFileSync(path.join(root,'evaluation/web-parity.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
if(differences.length)process.exitCode=1;
