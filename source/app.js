const DATA=JSON.parse(document.querySelector('#profile-data').textContent); const CFG=DATA.config, RT=DATA.runtime;
const $=(s,r=document)=>r.querySelector(s); const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const fmt=v=>Number.isFinite(Number(v))?new Intl.NumberFormat('en-US').format(Number(v)):'—';
const clamp=x=>Math.max(0,Math.min(1,x));
const chars=(text,cls)=>[...String(text??'')].map((ch,i)=>`<span class="${cls}" data-char="${i}">${ch===' '?'&nbsp;':esc(ch)}</span>`).join('');
function owl(){return `<pre class="owl" aria-label="THOTH owl emblem">  ╱\\ ╱\\\n ╱  V  \\\n│  • •  │\n ╲  ^  ╱\n  ╲___╱</pre>`}
function hero(){
  const id=CFG.identity;
  return `<section class="hero capture" data-capture="hero">
    <div class="hero-mark">${owl()}<div><div class="handle">${esc(id.handle)}</div><div class="wordmark">${esc(id.wordmark)}</div></div></div>
    <div class="hello" aria-label="${esc(id.hero_lines.join(' '))}">${id.hero_lines.map((x,i)=>`<div class="hello-row" data-row="${i}">${chars(x,'hello-char')}<i class="ink-head" aria-hidden="true"></i></div>`).join('')}</div>
    <div class="console">
      <div class="console-label">profile.trace</div>
      ${id.console.map((x,i)=>`<div class="console-line" data-line="${i}"><span class="prompt">›</span><span class="typed">${chars(x,'console-char')}</span><i class="line-cursor" aria-hidden="true"></i></div>`).join('')}
      <nav class="global-links">${(CFG.global_links||[]).filter(x=>x.url).map(x=>`<a href="${esc(x.url)}">${esc(x.label)} <i>↗</i></a>`).join('')}</nav>
    </div>
  </section>`
}
function stats(){
  const a=RT.account||{};
  const vals=[[a.commits_label||'COMMITS',a.commits],['RELEASES',a.releases],['FOLLOWERS',a.followers]];
  const group=vals.map(([k,v])=>`<span class="stat-unit"><b>${fmt(v)}</b><em>${esc(k)}</em></span>`).join('<span class="stat-sep">—</span>');
  return `<section class="stats capture" data-capture="stats"><div class="stats-track"><div class="stats-group">${group}</div></div></section>`
}
function mediaItem(m,i,p){
  if(m.type==='iframe') return `<figure class="media-card" data-media="${i}"><iframe ${m.srcdoc?`srcdoc="${esc(m.srcdoc)}"`:`src="${esc(m.src)}"`} title="${esc(p.name)} — ${esc(m.label)}"></iframe><figcaption>${esc(m.label)}</figcaption></figure>`;
  return `<figure class="media-card" data-media="${i}"><img src="${esc(m.src)}" alt="${esc(p.name)} — ${esc(m.label||('View '+(i+1)))}"><figcaption>${esc(m.label||('View '+(i+1)))}</figcaption></figure>`
}
function project(p,i){
  const media=(p.media||[]).slice(0,5), links=(p.links||[]).filter(x=>x.url).slice(0,5);
  return `<section class="project capture" data-capture="project-${esc(p.slug)}" data-slug="${esc(p.slug)}">
    <div class="project-number">0${i+1}</div>
    <div class="project-copy"><div class="project-status">${esc(p.status||'Public project')}</div><h2>${esc(p.name)}</h2><p class="project-lead">${esc(p.headline)}</p><p class="project-overview">${esc(p.overview)}</p><div class="pillars">${(p.pillars||[]).slice(0,6).map(x=>`<span>${esc(x)}</span>`).join('')}</div><div class="project-meta">${p.language?`<span>${esc(p.language)}</span>`:''}${p.updated?`<span>updated ${esc(p.updated)}</span>`:''}</div></div>
    <div class="project-visual ${media.length?'':'is-empty'}">${p.logo?`<img class="project-logo" src="${esc(p.logo)}" alt="${esc(p.name)} logo">`:''}${media.length?`<div class="stack">${media.map((m,n)=>mediaItem(m,n,p)).join('')}</div>`:`<div class="no-media"><span>Project media</span><strong>Real assets only.</strong><p>Add <code>.github/profile/cover-01.png</code> (and more covers) to this repository. No generated placeholder artwork is substituted.</p></div>`}</div>
    <div class="cta-row">${links.map((x,n)=>`<a class="cta" data-cta="${esc(p.slug)}-${n}" href="${esc(x.url)}"><span>${esc(x.label)}</span><i>↗</i></a>`).join('')}</div>
  </section>`
}
function calendarData(){
  if(Array.isArray(RT.contribution_weeks)&&RT.contribution_weeks.length){
    return RT.contribution_weeks.slice(-53).map(w=>({days:(w.days||[]).map(d=>({date:d.date,count:Number(d.count)||0,level:Number(d.level)||0}))}));
  }
  const levels=(RT.contribution_levels||[]).slice(-371), weeks=[];
  for(let i=0;i<levels.length;i+=7) weeks.push({days:levels.slice(i,i+7).map(level=>({date:'',count:0,level:Number(level)||0}))});
  return weeks.slice(-53);
}
function calendarMarkup(){
  const weeks=calendarData(), monthMarks=[]; let lastMonth='';
  weeks.forEach((w,wi)=>{
    const first=(w.days||[]).find(d=>d.date);
    if(!first)return;
    const dt=new Date(first.date+'T00:00:00Z'); const month=dt.toLocaleString('en-US',{month:'short',timeZone:'UTC'}).toUpperCase();
    if(month!==lastMonth){monthMarks.push({wi,month});lastMonth=month}
  });
  const monthAxis=monthMarks.map(m=>`<span style="--week:${m.wi}">${esc(m.month)}</span>`).join('');
  const cells=weeks.map((w,wi)=>`<div class="contrib-week" data-week="${wi}">${Array.from({length:7},(_,di)=>{const d=w.days[di]||{date:'',count:0,level:0};return `<i data-week="${wi}" data-day="${di}" style="--level:${Math.max(0,Math.min(4,d.level))}" title="${esc(d.date)}${d.date?' — ':''}${d.count} contributions"></i>`}).join('')}</div>`).join('');
  return `<div class="calendar-shell"><div class="month-axis">${monthAxis}</div><div class="weekday-axis"><span style="--day:1">MON</span><span style="--day:3">WED</span><span style="--day:5">FRI</span></div><div class="calendar-grid">${cells}<b class="calendar-scan" aria-hidden="true"></b></div></div>`
}
function commitPlan(commits){
  if(!commits.length)return '<div class="activity-empty">No recent public commits available.</div>';
  const xs=[24,52,34,62,42], ys=commits.map((_,i)=>30+i*60), pts=commits.map((_,i)=>`${xs[i%xs.length]},${ys[i]}`).join(' ');
  const rows=commits.map((c,i)=>`<a class="commit-row" href="${esc(c.url||'#')}" data-commit="${i}" style="--node-x:${xs[i%xs.length]}px"><span class="route-node" aria-hidden="true"></span><span class="commit-card"><span class="commit-top"><time>${esc(c.date)}</time><strong>${esc(c.repo)}</strong><code>${esc(c.sha)}</code></span><span class="commit-message">${esc(c.message)}</span></span></a>`).join('');
  return `<div class="commit-plan"><svg class="commit-route" viewBox="0 0 90 ${Math.max(300,commits.length*60)}" preserveAspectRatio="none" aria-hidden="true"><polyline points="${pts}"/><circle class="route-head" cx="${xs[0]}" cy="${ys[0]}" r="4"/></svg>${rows}</div>`
}
function activity(){
  const a=RT.account||{}, commits=(RT.recent_commits||[]).slice(0,5);
  return `<section class="activity capture" data-capture="activity">
    <div class="activity-title"><span>ACTIVITY / 12M</span><h2>Development trace.</h2></div>
    <div class="activity-stats"><div><b>${fmt(a.commits)}</b><span>${esc(a.commits_label||'COMMITS')}</span></div><div><b>${fmt(a.contributions_12m)}</b><span>CONTRIBUTIONS / 12M</span></div><div><b>${fmt(a.active_days_12m)}</b><span>ACTIVE DAYS / 12M</span></div></div>
    <div class="activity-body"><section class="calendar-panel"><div class="panel-kicker">CONTRIBUTION RHYTHM</div>${calendarMarkup()}<div class="calendar-footer"><span>${fmt(a.active_days_12m)} active days</span><span class="legend">LESS <i style="--level:0"></i><i style="--level:1"></i><i style="--level:2"></i><i style="--level:3"></i><i style="--level:4"></i> MORE</span></div></section><section class="commit-panel"><div class="panel-kicker">RECENT COMMITS</div>${commitPlan(commits)}</section></div>
  </section>`
}
$('#app').innerHTML=hero()+stats()+(RT.projects||[]).slice(0,3).map(project).join('')+activity();

let frameT=.42, ctaT=.2;
function ease(x){return 1-Math.pow(1-clamp(x),3)}
function setHero(t){
  document.documentElement.style.setProperty('--hero-t',t);
  const heroChars=$$('.hello-char'), hStart=.035, hEnd=.31, hHead=clamp((t-hStart)/(hEnd-hStart))*heroChars.length;
  heroChars.forEach((e,i)=>e.style.setProperty('--ink',clamp(hHead-i).toFixed(4)));
  $$('.hello-row').forEach(row=>{
    const rowChars=$$('.hello-char',row), first=heroChars.indexOf(rowChars[0]), local=clamp((hHead-first)/Math.max(1,rowChars.length));
    row.style.setProperty('--write',local.toFixed(4));
  });
  const consoleChars=$$('.console-char'), cStart=.34, cEnd=.91, cHead=clamp((t-cStart)/(cEnd-cStart))*consoleChars.length;
  consoleChars.forEach((e,i)=>e.style.setProperty('--typed',clamp(cHead-i).toFixed(4)));
  let offset=0; $$('.console-line').forEach((line,li)=>{
    const count=$$('.console-char',line).length, p=clamp(cHead-offset), done=cHead>=offset+count, active=cHead>=offset&&cHead<offset+count;
    line.style.setProperty('--line-on',cHead>=offset?1:0); line.style.setProperty('--cursor-on',(active||(li===$$('.console-line').length-1&&t>.91))?1:0); line.style.setProperty('--line-progress',count?clamp((cHead-offset)/count):0); offset+=count;
  });
}
function setStats(t){const drift=Math.sin(t*Math.PI*2)*26;document.documentElement.style.setProperty('--marquee-x',drift.toFixed(3)+'px')}
function setProject(slug,t){const sec=document.querySelector(`[data-slug="${CSS.escape(slug)}"]`); if(!sec)return; sec.style.setProperty('--pt',t); const cards=$$('.media-card',sec); if(cards.length){const phase=(t*cards.length)%cards.length,active=Math.floor(phase); cards.forEach((c,i)=>{let pos=(i-active+cards.length)%cards.length;c.style.setProperty('--pos',pos);c.style.setProperty('--frac',phase-active)})}}
function setActivity(t){
  const sec=$('.activity'); if(!sec)return; const tt=clamp(t); sec.style.setProperty('--at',tt);
  const weeks=$$('.contrib-week',sec), sweep=-2+tt*(weeks.length+4); weeks.forEach((w,wi)=>{const scan=Math.max(0,1-Math.abs(wi-sweep)/2.5); w.style.setProperty('--scan',scan.toFixed(4))});
  const route=$('.commit-route polyline',sec), head=$('.route-head',sec); if(route){const len=route.getTotalLength(); route.style.strokeDasharray=String(len); route.style.strokeDashoffset=String(len*(1-Math.max(.03,tt))); if(head){const p=route.getPointAtLength(len*tt); head.setAttribute('cx',p.x); head.setAttribute('cy',p.y); head.style.opacity=String(.2+.8*Math.sin(Math.PI*tt));}}
  $$('.commit-row',sec).forEach((row,i)=>{const reveal=clamp((tt-.06-i*.12)/.18);row.style.setProperty('--ci',reveal.toFixed(4))});
}
window.__THOTH_RENDER_CTA=t=>{ctaT=t;document.documentElement.style.setProperty('--cta-t',t)};
window.__THOTH_RENDER_FRAME=(scene,t)=>{frameT=t;if(scene==='hero'||scene==='all')setHero(t);if(scene==='stats'||scene==='all')setStats(t);if(scene.startsWith('project-'))setProject(scene.slice(8),t);if(scene==='all')(RT.projects||[]).forEach(p=>setProject(p.slug,t));if(scene==='activity'||scene==='all')setActivity(t);window.__THOTH_RENDER_CTA(t)};
window.__THOTH_RENDER_FRAME('all',.42);
