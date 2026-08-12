(async function(){
  // 去重: window.__xf2 → window.__xuniq2（按 screen_name 小写）
  const seen = new Map();
  for (const x of window.__xf2) { if (!seen.has(x.s.toLowerCase())) seen.set(x.s.toLowerCase(), x); }
  window.__xuniq2 = Array.from(seen.values());
  return 'UNIQ:' + window.__xuniq2.length;
})()
