// 取按钮坐标: profile 页 [data-testid$="-unfollow"] 中心点
// 返回 {"x":..,"y":..} 或 NO_BTN
(function(){
  const b = document.querySelector('[data-testid$="-unfollow"]');
  if (!b) return 'NO_BTN';
  const r = b.getBoundingClientRect();
  return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
})()
