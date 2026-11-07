import {buildCandidate} from '../lib/publish.js';
let input='';for await(const c of process.stdin)input+=c;
process.stdout.write(JSON.stringify(await buildCandidate(JSON.parse(input))));
