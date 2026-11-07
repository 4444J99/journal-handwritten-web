// This directory is private source, never a public Pages deployment artifact.
// Approved public readers are built separately by studio-cf/build_reader.py.
export default {
  fetch() {
    return new Response(null, {status:403, headers:{'cache-control':'no-store','x-robots-tag':'noindex, nofollow'}});
  },
};
