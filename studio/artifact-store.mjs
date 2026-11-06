import {createRevisionStore} from './notes-store.mjs';
import {assertArtifact} from './artifact-model.mjs';
export function createArtifactStore(options) {
  return createRevisionStore({...options,collections:['artifacts'],backupFormat:'versforms-artifacts-backup',validate:assertArtifact});
}
