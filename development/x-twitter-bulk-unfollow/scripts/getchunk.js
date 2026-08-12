(async function(){
  // 分块导出: 把 START_HERE 替换为起始下标后执行
  // 用法: sed "s/START_HERE/$start/" getchunk.js → Runtime.evaluate → 写 chunk_$start.json
  const s = parseInt('START_HERE');
  return JSON.stringify((window.__xuniq2 || []).slice(s, s + 400));
})()
