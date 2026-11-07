import {handlePublish} from '../../../lib/publish-api.js';
export function onRequest({request,env,data}) {return handlePublish(request,env,data.user);}
