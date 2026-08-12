(async function(){
  // X Following 批量抓取（断点续传 + 429 降速）
  // 用法: 每次 Runtime.evaluate 调用此脚本，数据累积在 window.__xf2 + window.__xcursor2
  // 前置: 从 gettoken.js 获取 bearer + queryId，替换下方 BEARER 和 queryId
  const ct0 = document.cookie.split('; ').find(c=>c.startsWith('ct0='));
  const csrf = ct0 ? ct0.split('=')[1] : '';
  const BEARER = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'; // 会轮换，用 gettoken.js 提取
  const QUERY_ID = 'b8XpwALENnJdFSHchkK6rw'; // 会变，用 gettoken.js 提取
  const USER_ID = '1277546358593863680'; // 目标账号 @200dandan 的 userID
  const features = {
    rweb_video_screen_enabled: true, profile_label_improvements_pcf_label_in_post_enabled: true,
    responsive_web_graphql_exclude_direct_when_unfollowed: true, verified_phone_label_enabled: true,
    creator_subscriptions_tweet_preview_api_enabled: true, responsive_web_graphql_timeline_navigation_enabled: true,
    responsive_web_graphql_skip_user_profile_image_extensions_enabled: false, tweetypie_unmention_optimization_enabled: true,
    responsive_web_edit_tweet_api_enabled: true, graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
    view_counts_everywhere_api_enabled: true, longform_notetweets_consumption_enabled: true,
    responsive_web_twitter_article_tweet_consumption_enabled: true, tweet_awards_web_tipping_enabled: false,
    creator_subscriptions_quote_tweet_preview_enabled: false, longform_notetweets_rich_text_read_enabled: true,
    longform_notetweets_inline_media_enabled: true, profile_foundations_timeline_tweet_count_enabled: true,
    responsive_web_enhance_cards_enabled: false
  };
  window.__xf2 = window.__xf2 || [];
  let cursor = window.__xcursor2 || null;
  let pages = 0;
  let lastErr = null;
  while (pages < 4) { // 每调用抓 4 页（约 200 用户），规避 429
    const vars = {userId:USER_ID,count:100,includePromotedContent:false,withSuperFollowsUserFields:true,withUserResults:true,withBirdwatchPivots:false,withReactionsMetadata:false,withReactionsPerspective:false,withSignupRequired:false,features:features};
    if (cursor) vars.cursor = cursor;
    try {
      const r = await fetch('https://x.com/i/api/graphql/' + QUERY_ID + '/Following?variables=' + encodeURIComponent(JSON.stringify(vars)), {
        headers: {'authorization': 'Bearer ' + BEARER, 'x-csrf-token': csrf, 'x-twitter-auth-type': 'OAuth2Session', 'x-twitter-client-language': 'zh-cn', 'x-twitter-active-user': 'yes', 'content-type': 'application/json'}
      });
      if (r.status !== 200) { lastErr = 'STATUS:' + r.status; break; }
      const j = await r.json();
      const inst = j.data.user.result.timeline.timeline.instructions;
      const entries = (inst.find(i=>i.type==='TimelineAddEntries')||{}).entries || [];
      let newCursor = null;
      for (const e of entries) {
        if (e.content.entryType === 'TimelineTimelineCursor') {
          if (e.content.cursorType === 'Bottom') { newCursor = e.content.value || null; }
          continue;
        }
        const u = e.content.itemContent?.user_results?.result;
        if (u && u.core && u.core.screen_name) {
          const rc = u.relationship_counts || {};
          window.__xf2.push({
            s: u.core.screen_name, f: rc.followers || 0, st: (u.tweet_counts||{}).tweets || 0,
            v: !!u.is_blue_verified, pr: !!(u.privacy||{}).protected,
            ca: u.core.created_at || '', n: (u.core.name||'').slice(0,60), d: ((u.profile_bio||{}).description||'').slice(0,120)
          });
        }
      }
      if (newCursor && newCursor === cursor) { lastErr = 'CURSOR_STUCK'; break; } // 深度上限 ~7500
      cursor = newCursor;
      pages++;
      await new Promise(res=>setTimeout(res, 800));
    } catch(e) { lastErr = 'ERR:' + e.message; break; }
  }
  window.__xcursor2 = cursor;
  const uniq = new Set(window.__xf2.map(x=>x.s.toLowerCase())).size;
  return 'TOTAL:' + window.__xf2.length + ' UNIQ:' + uniq + (lastErr ? ' ERR:' + lastErr : '') + (cursor ? ' MORE' : ' DONE');
})()
