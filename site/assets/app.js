(()=>{'use strict';
const $=id=>document.getElementById(id);
const esc=(v)=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const comma=v=>(typeof v==='number'&&Number.isFinite(v))?v.toLocaleString('ja-JP'):'—';
const fmtStars=v=>typeof v==='number'?'+'+comma(v):'未取得';
const safeLink=repo=>/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/.test(repo.url||'')?repo.url:'#';
const periodTitle={daily:'今日増えたスター',weekly:'今週増えたスター',monthly:'今月増えたスター'};
const periodName={daily:'日次',weekly:'週間',monthly:'月間'};
const defs=['AI・エージェント','開発ツール','セキュリティ','デザイン・制作','クラウド・インフラ','データ・分析','ゲーム・エンタメ','学習・教育','その他'];
const state={period:'weekly',scale:'linear',snapshot:null,previous:null,dates:[],dateIndex:0,search:'',category:'',order:'official',isDemo:false};
function status(text,type='live'){$('notice').textContent=text;$('notice').dataset.state=type;}
async function getJson(url){const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json();}
function snapshotPath(dateEntry){return './'+dateEntry.path.replace(/^\/+/, '');}
function validSnapshot(s){return s&&s.periods&&s.periods.daily&&s.periods.weekly&&s.periods.monthly;}
async function init(){
  const preview = location.protocol==='file:'||new URLSearchParams(location.search).has('demo');
  if(preview){activateDemo();return;}
  try{
    const index=await getJson('./data/index.json?t='+Date.now());
    if(!Array.isArray(index.dates)||index.dates.length===0)throw new Error('履歴ファイルが空です');
    state.dates=index.dates;
    for(const entry of index.dates){const option=document.createElement('option');option.value=entry.date;option.textContent=entry.date+' 取得';$('snapshot').appendChild(option);}
    $('snapshot').querySelector('option:first-child')?.remove();
    await selectDate(0);
  }catch(error){
    status('実データがまだありません。GitHub Actions の「Collect GitHub Trending」を手動実行すると、最新ランキングが反映されます。取得エラー: '+error.message,'error');
    $('update-status').textContent='未取得';$('snapshot').innerHTML='<option value="">履歴なし</option>';
    $('rankings').innerHTML='<div class="empty loading-fail">現在、検証済みランキングはありません。サンプル数値を実データとして表示しない設計です。ローカルでお試しする場合はURL末尾に <code>?demo=1</code> を付けてください。</div>';
    $('brief').innerHTML='<div class="empty">初回データ収集待ちです。</div>';
    $('category-bars').innerHTML='<div class="empty">初回データ収集待ちです。</div>';
    $('spotlight').innerHTML='';$('keywords').innerHTML='';
  }
}
function activateDemo(){
  if(!validSnapshot(window.GH_NEWS_DEMO))return;
  state.isDemo=true;state.snapshot=window.GH_NEWS_DEMO;state.previous=null;state.dates=[{date:state.snapshot.date_jst}];
  $('snapshot').innerHTML='<option>ローカル表示サンプル</option>';render();
  status('表示サンプル：ランキングとスター数は架空の値です。実データではありません。GitHub Actionsの収集が成功すると本番サイトに実測値が表示されます。','demo');
}
async function selectDate(idx){
  if(idx<0||idx>=state.dates.length)return;
  state.dateIndex=idx;const entry=state.dates[idx];
  const previous=state.dates[idx+1];
  $('update-status').textContent='取得データを確認中';
  try{
    const [now,prev]=await Promise.all([getJson(snapshotPath(entry)+'?r='+encodeURIComponent(entry.captured_at||'')), previous?getJson(snapshotPath(previous)+'?r='+encodeURIComponent(previous.captured_at||'')).catch(()=>null):Promise.resolve(null)]);
    if(!validSnapshot(now))throw new Error('保存データの形式が不正です');
    state.snapshot=now;state.previous=validSnapshot(prev)?prev:null;
    state.isDemo=!!now.is_demo;
    $('snapshot').value=entry.date;
    status('', 'live');render();
  }catch(e){status('取得日に対応するデータを読み込めませんでした: '+e.message,'error');}
}
function changes(rows){
  const old=state.previous?.periods?.[state.period]?.repositories||[];
  if(!old.length)return null;
  const map=new Map(old.map(r=>[r.full_name.toLowerCase(),r.rank]));
  return {map,newcomers:rows.filter(r=>!map.has(r.full_name.toLowerCase())),climbers:rows.map(r=>({...r,change:(map.get(r.full_name.toLowerCase())||r.rank)-r.rank})).filter(r=>map.has(r.full_name.toLowerCase())&&r.change>0).sort((a,b)=>b.change-a.change)};
}
function render(){
  const snapshot=state.snapshot;if(!snapshot)return;
  const rows=snapshot.periods?.[state.period]?.repositories||[];
  const compare=changes(rows);
  $('edition-date').textContent=snapshot.date_jst+' (JST)';
  $('update-status').textContent=state.isDemo?'DEMO / 架空データ':'VERIFIED / 公開ページ取得';
  $('ranking-title').innerHTML=esc(periodTitle[state.period])+' <span class="headline-deco">★</span>';
  const valid=rows.filter(r=>typeof r.stars_period==='number').sort((a,b)=>b.stars_period-a.stars_period);
  $('stat-repos').textContent=comma(rows.length);
  $('stat-stars').textContent=valid.length?fmtStars(valid[0].stars_period):'—';
  $('stat-stars-desc').textContent=valid.length?valid[0].full_name:'増加値を取得できませんでした';
  $('stat-new').textContent=compare?comma(compare.newcomers.length):'—';
  const categories=new Set(rows.map(r=>r.category||'その他'));
  $('stat-categories').textContent=comma(categories.size);
  const filter=$('category-filter'), keep=filter.value;
  filter.innerHTML='<option value="">すべてのカテゴリ</option>'+Array.from(categories).sort((a,b)=>defs.indexOf(a)-defs.indexOf(b)).map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  filter.value=categories.has(keep)?keep:'';state.category=filter.value;
  drawRankings(rows,compare);drawBrief(rows,compare);drawCategories(rows);drawSpotlight(rows);drawKeywords(rows);
}
function drawRankings(rows,compare){
  const term=state.search.toLocaleLowerCase();
  let list=rows.filter(r=>(!state.category||r.category===state.category)&&(!term||[r.full_name,r.description,r.category,r.language].some(v=>String(v||'').toLowerCase().includes(term))));
  if(state.order==='stars')list=[...list].sort((a,b)=>(b.stars_period??-1)-(a.stars_period??-1));
  list=list.slice(0,10); // The ranking component is explicitly a TOP 10.
  const max=Math.max(1,...rows.map(r=>typeof r.stars_period==='number'?r.stars_period:0));
  if(!list.length){$('rankings').innerHTML='<p class="empty">条件に一致するリポジトリがありません。</p>';return;}
  $('rankings').innerHTML=list.map(r=>{
    const ratio=typeof r.stars_period==='number'?Math.max(.02,state.scale==='sqrt'?Math.sqrt(r.stars_period/max):r.stars_period/max):0;
    const before=compare?.map.get(r.full_name.toLowerCase());
    const movement=before&&before>r.rank?`<span class="rank-moving">↑${before-r.rank}</span>`:before&&before<r.rank?`<span class="rank-moving" style="color:#a17b71">↓${r.rank-before}</span>`:'';
    return `<div class="rank-row"><div class="rank-pos ${r.rank<=3?'top':''}">${r.rank}</div><div class="rank-identity"><a class="rank-name" href="${esc(safeLink(r))}" target="_blank" rel="noopener noreferrer" title="GitHubで開く">${esc(r.full_name)} ↗${movement}</a><div class="rank-desc" title="${esc(r.description||'説明なし')}">${esc(r.description||'説明文なし')}</div></div><div><div class="rank-category">${esc(r.category||'その他')}</div></div><div class="barslot" title="${esc(fmtStars(r.stars_period))}"><div class="bar ${r.rank<=3?'top':''}" style="width:${(ratio*100).toFixed(2)}%"></div></div><div class="star-number">${esc(fmtStars(r.stars_period))}</div></div>`;
  }).join('');
}
function drawBrief(rows,compare){
  const top=rows.filter(r=>typeof r.stars_period==='number').sort((a,b)=>b.stars_period-a.stars_period)[0];
  const count={};rows.forEach(r=>count[r.category||'その他']=(count[r.category||'その他']||0)+1);
  const leading=Object.entries(count).sort((a,b)=>b[1]-a[1])[0];
  let items=[];
  if(rows.length){items.push({icon:'★',head:'今回のスター増加トップ',desc:top?`${top.full_name} が${fmtStars(top.stars_period)}。この値は${periodName[state.period]}の増加分です。`:'増加スター数を取得できませんでした。'});}
  if(leading)items.push({icon:'▦',head:`「${leading[0]}」が最多`,desc:`掲載${rows.length}件中${leading[1]}件。ジャンルは名前と説明文から推定しています。`});
  if(compare){
    if(compare.newcomers.length)items.push({icon:'↗',head:`前回から${compare.newcomers.length}件が新規ランクイン`,desc:`例：${compare.newcomers.slice(0,2).map(x=>x.full_name).join('、')}。同じ集計期間の前回取得と比較。`});
    else items.push({icon:'↗',head:'前回からの新規ランクインは0件',desc:'同じ集計期間で比較した結果です。'});
    if(compare.climbers.length)items.push({icon:'↑',head:`順位上昇: ${compare.climbers[0].full_name}`,desc:`前回の${compare.climbers[0].rank+compare.climbers[0].change}位から${compare.climbers[0].rank}位へ上昇しました。`});
  }else items.push({icon:'◷',head:'前回との差分は蓄積待ち',desc:'日次スナップショットが2件以上になると新規ランクインや順位上昇を自動判定します。'});
  $('brief').innerHTML=items.slice(0,4).map(x=>`<div class="brief-item"><div class="brief-icon">${esc(x.icon)}</div><div><strong>${esc(x.head)}</strong><p>${esc(x.desc)}</p></div></div>`).join('');
}
function drawCategories(rows){
  const count={};for(const repo of rows){const cat=repo.category||'その他';count[cat]=(count[cat]||0)+1;}
  const entries=Object.entries(count).sort((a,b)=>b[1]-a[1]);
  const max=entries[0]?.[1]||1;
  $('category-bars').innerHTML=entries.map(([name,n])=>`<div class="category-row"><div class="category-label">${esc(name)}</div><div class="category-bg"><div class="category-fill" style="width:${(100*n/max).toFixed(1)}%"></div></div><div class="category-num">${n}</div></div>`).join('');
}
function drawSpotlight(rows){
  $('spotlight').innerHTML=rows.slice(0,3).map(r=>`<div class="spot-card"><div class="spot-head"><span class="spot-rank">${r.rank}</span><a class="spot-name" target="_blank" rel="noopener noreferrer" href="${esc(safeLink(r))}">${esc(r.full_name)} ↗</a></div><p class="spot-description">${esc(r.intro_ja||'GitHubで公開されているプロジェクトです。')}</p><p class="spot-original">${esc(r.description||'公式説明文は掲載されていません。')}</p><div class="spot-bottom"><div class="language">${esc(r.language||'言語未記載')}</div><div class="spot-stars">${esc(fmtStars(r.stars_period))}<small>${esc(periodName[state.period])}スター増加</small></div></div></div>`).join('');
}
function drawKeywords(rows){
  const keywords=[['agent',/\bagents?\b|agentic/i],['LLM',/\bllm\b|large language model/i],['AI',/\bai\b|artificial intelligence/i],['plugin',/\bplugins?\b|extension/i],['security',/secur|cyber|malware/i],['coding',/cod(e|ing)|developer|editor/i],['design',/design|diagram|graphic/i],['video',/\bvideo\b|animation/i],['data',/\bdata\b|analytics|\bsql\b/i],['cloud',/cloud|kubernetes|server|deploy/i],['game',/\bgame\b|gaming|emulat/i],['open source',/open.source|\boss\b/i]];
  const score=keywords.map(([term,re])=>({term,count:rows.filter(r=>re.test(r.full_name+' '+(r.description||''))).length})).filter(x=>x.count>0).sort((a,b)=>b.count-a.count).slice(0,10);
  $('keywords').innerHTML=score.length?score.map((x,i)=>`<span class="keyword"><b>${i+1}</b> ${esc(x.term)} <small>${x.count}</small></span>`).join(''):'<span class="empty">判定可能なキーワードなし</span>';
}
$('period').addEventListener('change',event=>{state.period=event.target.value;render();});
$('snapshot').addEventListener('change',event=>{const i=state.dates.findIndex(e=>e.date===event.target.value);if(i!==-1)selectDate(i);});
$('repo-search').addEventListener('input',event=>{state.search=event.target.value;const rows=state.snapshot?.periods?.[state.period]?.repositories||[];drawRankings(rows,changes(rows));});
$('category-filter').addEventListener('change',event=>{state.category=event.target.value;const rows=state.snapshot?.periods?.[state.period]?.repositories||[];drawRankings(rows,changes(rows));});
$('order').addEventListener('change',event=>{state.order=event.target.value;const rows=state.snapshot?.periods?.[state.period]?.repositories||[];drawRankings(rows,changes(rows));});
for(const [id,mode] of [['scale-linear','linear'],['scale-sqrt','sqrt']]){$(id).addEventListener('click',()=>{state.scale=mode;$('scale-linear').classList.toggle('active',mode==='linear');$('scale-sqrt').classList.toggle('active',mode==='sqrt');const rows=state.snapshot?.periods?.[state.period]?.repositories||[];drawRankings(rows,changes(rows));});}
init();
})();
