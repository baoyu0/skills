(async function(){
  try {
    const r = await fetch('https://abs.twimg.com/responsive-web/client-web/main.cec9b1ca.js');
    const t = await r.text();
    const b = t.indexOf('AAAAAAAA');
    const q = t.indexOf('operationName:"Following"');
    let qid = '';
    if (q > -1) {
      const seg = t.slice(Math.max(0, q - 130), q + 90);
      const m = seg.match(/queryId:"([A-Za-z0-9_-]+)"/);
      qid = m ? m[1] : '';
    }
    return JSON.stringify({bearer: b > -1 ? t.slice(b, b + 180) : 'NONE', qid: qid});
  } catch(e) { return 'ERR:' + e.message; }
})()
