const DATA=JSON.parse(document.querySelector('#profile-data').textContent); const CFG=DATA.config, RT=DATA.runtime;
const $=(s,r=document)=>r.querySelector(s); const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const fmt=v=>Number.isFinite(Number(v))?new Intl.NumberFormat('en-US').format(Number(v)):'—';
const clamp=x=>Math.max(0,Math.min(1,x));
const APPLE_SPEED=1.1;
const HERO_CHAR_RATE=25;
const HERO_LINE_PAUSE=.075;
const APPLE_HERO={"systems":{"vb":[-53,-1424,7912,1922],"glyphs":[{"i":0,"d":"M447 25C718 25 940 -121 940 -349C940 -481 853 -561 671 -601L488 -640C414 -656 374 -686 374 -736C374 -820 463 -890 584 -890C691 -890 757 -829 744 -727H981C983 -745 985 -763 985 -779C985 -965 828 -1079 590 -1079C328 -1079 120 -934 120 -716C120 -578 214 -488 390 -450L564 -413C639 -396 681 -368 681 -317C681 -225 575 -164 453 -164C332 -164 271 -221 277 -326H28C27 -316 27 -306 27 -296C27 -87 202 25 447 25Z"},{"i":1,"d":"M1009 418H1174C1324 418 1446 336 1534 174L2210 -1056H1935L1650 -506C1611 -429 1573 -351 1536 -273C1525 -350 1512 -428 1499 -506L1396 -1056H1140L1373 -6L1318 96C1274 179 1236 213 1168 213H1043Z"},{"i":2,"d":"M2588 25C2859 25 3081 -121 3081 -349C3081 -481 2994 -561 2812 -601L2629 -640C2555 -656 2515 -686 2515 -736C2515 -820 2604 -890 2725 -890C2832 -890 2898 -829 2885 -727H3122C3124 -745 3126 -763 3126 -779C3126 -965 2969 -1079 2731 -1079C2469 -1079 2261 -934 2261 -716C2261 -578 2355 -488 2531 -450L2705 -413C2780 -396 2822 -368 2822 -317C2822 -225 2716 -164 2594 -164C2473 -164 2412 -221 2418 -326H2169C2168 -316 2168 -306 2168 -296C2168 -87 2343 25 2588 25Z"},{"i":3,"d":"M3933 -1056H3718L3765 -1344H3513L3465 -1056H3280L3246 -853H3431L3334 -266C3305 -85 3391 0 3607 0H3759L3792 -203H3684C3602 -203 3581 -228 3593 -303L3684 -853H3899Z"},{"i":4,"d":"M4397 24C4666 24 4851 -118 4925 -331H4685C4646 -238 4554 -174 4416 -174C4235 -174 4194 -286 4197 -426C4692 -435 4960 -502 4960 -765C4960 -972 4792 -1080 4563 -1080C4225 -1080 3971 -839 3950 -463C3929 -131 4112 24 4397 24ZM4216 -602C4251 -756 4343 -880 4537 -880C4656 -880 4719 -835 4719 -762C4719 -662 4619 -610 4216 -602Z"},{"i":5,"d":"M5040 0H5292L5395 -622C5420 -773 5539 -863 5660 -863C5765 -863 5826 -796 5807 -681L5695 0H5940L6046 -640C6067 -766 6169 -863 6304 -863C6404 -863 6476 -809 6453 -670L6343 0H6596L6709 -689C6750 -937 6612 -1077 6406 -1077C6255 -1077 6121 -1002 6046 -879C6017 -996 5910 -1077 5766 -1077C5641 -1077 5516 -1017 5431 -886L5458 -1056H5214Z"},{"i":6,"d":"M7241 25C7512 25 7734 -121 7734 -349C7734 -481 7647 -561 7465 -601L7282 -640C7208 -656 7168 -686 7168 -736C7168 -820 7257 -890 7378 -890C7485 -890 7551 -829 7538 -727H7775C7777 -745 7779 -763 7779 -779C7779 -965 7622 -1079 7384 -1079C7122 -1079 6914 -934 6914 -716C6914 -578 7008 -488 7184 -450L7358 -413C7433 -396 7475 -368 7475 -317C7475 -225 7369 -164 7247 -164C7126 -164 7065 -221 7071 -326H6822C6821 -316 6821 -306 6821 -296C6821 -87 6996 25 7241 25Z"}]},"built different.":{"vb":[-55,-1580,12937.21,2078],"glyphs":[{"i":0,"d":"M608 21C948 21 1148 -315 1148 -637C1148 -902 1001 -1077 760 -1077C631 -1077 503 -1026 431 -913H430L523 -1490H271L25 0H273L302 -173H303C353 -42 461 21 608 21ZM552 -190C418 -190 340 -280 340 -429C340 -636 471 -868 693 -868C819 -868 895 -788 895 -637C895 -423 774 -190 552 -190Z"},{"i":1,"d":"M1599 21C1745 21 1862 -43 1954 -162L1927 0H2176L2351 -1056H2098L1999 -459C1969 -279 1858 -200 1725 -200C1590 -200 1526 -281 1551 -436L1654 -1056H1401L1292 -396C1247 -125 1378 21 1599 21Z"},{"i":2,"d":"M2400 0H2652L2827 -1056H2575ZM2726 -1213C2812 -1213 2888 -1275 2901 -1357C2915 -1438 2860 -1500 2774 -1500C2688 -1500 2613 -1438 2599 -1357C2586 -1275 2640 -1213 2726 -1213Z"},{"i":3,"d":"M3376 -1490H3124L2877 0H3129Z"},{"i":4,"d":"M4086 -1056H3871L3918 -1344H3666L3618 -1056H3433L3399 -853H3584L3487 -266C3458 -85 3544 0 3760 0H3912L3945 -203H3837C3755 -203 3734 -228 3746 -303L3837 -853H4052Z"},{"i":6,"d":"M4950 21C5081 21 5200 -29 5286 -156H5287L5262 0H5510L5756 -1490H5504L5406 -896H5405C5356 -1014 5246 -1077 5102 -1077C4766 -1077 4561 -742 4561 -411C4561 -149 4707 21 4950 21ZM5016 -190C4890 -190 4815 -269 4815 -419C4815 -636 4937 -868 5157 -868C5291 -868 5369 -777 5369 -628C5369 -416 5234 -190 5016 -190Z"},{"i":7,"d":"M5734 0H5986L6161 -1056H5909ZM6060 -1213C6146 -1213 6222 -1275 6235 -1357C6249 -1438 6194 -1500 6108 -1500C6022 -1500 5947 -1438 5933 -1357C5920 -1275 5974 -1213 6060 -1213Z"},{"i":8,"d":"M6943 -1056H6728L6746 -1168C6761 -1254 6798 -1287 6884 -1287H6981L7015 -1490H6868C6659 -1490 6531 -1392 6501 -1210L6475 -1056H6290L6256 -853H6441L6285 83C6271 174 6237 206 6146 206H6068L6033 418H6166C6395 418 6500 313 6534 108L6694 -853H6910Z"},{"i":9,"d":"M7653 -1056H7438L7456 -1168C7471 -1254 7508 -1287 7594 -1287H7691L7725 -1490H7578C7369 -1490 7241 -1392 7211 -1210L7185 -1056H7000L6966 -853H7151L6995 83C6981 174 6947 206 6856 206H6778L6743 418H6876C7105 418 7210 313 7244 108L7404 -853H7620Z"},{"i":10,"d":"M8111 24C8380 24 8565 -118 8639 -331H8399C8360 -238 8268 -174 8130 -174C7949 -174 7908 -286 7911 -426C8406 -435 8674 -502 8674 -765C8674 -972 8506 -1080 8277 -1080C7939 -1080 7685 -839 7664 -463C7643 -131 7826 24 8111 24ZM7930 -602C7965 -756 8057 -880 8251 -880C8370 -880 8433 -835 8433 -762C8433 -662 8333 -610 7930 -602Z"},{"i":11,"d":"M8754 0H9006L9106 -598C9133 -763 9239 -846 9359 -846C9409 -846 9459 -841 9477 -838L9514 -1062C9494 -1064 9466 -1066 9433 -1066C9296 -1066 9205 -1002 9146 -881H9143L9172 -1056H8929Z"},{"i":12,"d":"M9963 24C10232 24 10417 -118 10491 -331H10251C10212 -238 10120 -174 9982 -174C9801 -174 9760 -286 9763 -426C10258 -435 10526 -502 10526 -765C10526 -972 10358 -1080 10129 -1080C9791 -1080 9537 -839 9516 -463C9495 -131 9678 24 9963 24ZM9782 -602C9817 -756 9909 -880 10103 -880C10222 -880 10285 -835 10285 -762C10285 -662 10185 -610 9782 -602Z"},{"i":13,"d":"M10955 -589C10985 -769 11099 -856 11239 -856C11367 -856 11431 -783 11406 -628L11302 0H11555L11662 -651C11708 -922 11570 -1077 11342 -1077C11204 -1077 11093 -1020 11003 -905L11028 -1056H10780L10606 0H10858Z"},{"i":14,"d":"M12511 -1056H12296L12343 -1344H12091L12043 -1056H11858L11824 -853H12009L11912 -266C11883 -85 11969 0 12185 0H12337L12370 -203H12262C12180 -203 12159 -228 12171 -303L12262 -853H12477Z"},{"i":15,"d":"M12636 18C12715 18 12787 -42 12800 -121C12815 -215 12752 -292 12659 -292C12580 -292 12508 -232 12495 -154C12480 -59 12543 18 12636 18Z"}]}};
const chars=(text,cls,{breakable=false}={})=>[...String(text??'')].map((ch,i)=>{
  if(ch===' '&&breakable) return `<span class="${cls} console-space" data-char="${i}">&nbsp;</span><wbr>`;
  return `<span class="${cls}" data-char="${i}">${ch===' '?'&nbsp;':esc(ch)}</span>`;
}).join('');
function owl(){return `<svg class="owl-sigil" viewBox="0 0 64 64" role="img" aria-label="THOTH owl sigil"><path class="owl-wing owl-wing-left" d="M31.8 20.5 21 8.5 7.5 18.2l7.3 25.1L31.8 56"/><path class="owl-wing owl-wing-right" d="m32.2 20.5 10.8-12 13.5 9.7-7.3 25.1L32.2 56"/><path class="owl-mask" d="M13.5 19.5 25 24.2 32 34.5l7-10.3 11.5-4.7-5.1 18.7L32 48.8 18.6 38.2Z"/><circle class="owl-eye" cx="22.5" cy="29.2" r="4.4"/><circle class="owl-eye" cx="41.5" cy="29.2" r="4.4"/><path class="owl-beak-line" d="m32 33.5-4.2 5.1 4.2 3.1 4.2-3.1Z"/><path class="owl-axis" d="M32 14.5V55.8"/><path class="owl-base" d="M18.5 48.5 32 57l13.5-8.5"/></svg>`}
function appleHeroLine(text,row){
  const spec=APPLE_HERO[text];
  if(!spec) return `<div class="hello-row hello-fallback" data-row="${row}">${chars(text,'hello-char')}</div>`;
  const [x,y,w,h]=spec.vb, ratio=w/h;
  const compound=spec.glyphs.map(g=>g.d).join(' ');
  const strokes=spec.glyphs.map((g,n)=>`<path class="hello-glyph-path" data-glyph="${n}" pathLength="1" d="${g.d}"/>`).join('');
  return `<div class="hello-row apple-row" data-row="${row}" style="--aspect:${ratio.toFixed(5)}"><svg class="hello-svg" viewBox="${x} ${y} ${w} ${h}" role="img" aria-label="${esc(text)}" preserveAspectRatio="xMinYMid meet"><path class="hello-line-fill" d="${compound}"/>${strokes}</svg></div>`;
}
function hero(){
  const id=CFG.identity;
  return `<section class="hero capture" data-capture="hero">
    <div class="hero-mark">${owl()}<div><div class="handle">${esc(id.handle)}</div><div class="wordmark">${esc(id.wordmark)}</div></div></div>
    <div class="hello" aria-label="${esc(id.hero_lines.join(' '))}">${id.hero_lines.map((x,i)=>appleHeroLine(x,i)).join('')}</div>
    <div class="console">
      <div class="console-label">profile.trace</div>
      ${id.console.map((x,i)=>`<div class="console-line" data-line="${i}" data-text="${esc(x)}"><span class="prompt">›</span><span class="typed"></span><i class="line-cursor" aria-hidden="true"></i></div>`).join('')}
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
  const tones=['#101214','#30343a','#5f656b','#a0a5a9','#f0f0ec'];
  weeks.forEach((w,wi)=>{
    const first=(w.days||[]).find(d=>d.date);
    if(!first)return;
    const dt=new Date(first.date+'T00:00:00Z'); const month=dt.toLocaleString('en-US',{month:'short',timeZone:'UTC'}).toUpperCase();
    if(month!==lastMonth){monthMarks.push({wi,month});lastMonth=month}
  });
  const visibleMonths=monthMarks.filter((m,i)=>!(i===0&&monthMarks[1]&&monthMarks[1].wi-m.wi<3));
  const monthAxis=visibleMonths.map(m=>`<span style="--week:${m.wi}">${esc(m.month)}</span>`).join('');
  const cells=weeks.map((w,wi)=>`<div class="contrib-week" data-week="${wi}">${Array.from({length:7},(_,di)=>{
    const d=w.days[di]||{date:'',count:0,level:0};
    const level=Math.max(0,Math.min(4,Number(d.level)||0));
    const count=Math.max(0,Number(d.count)||0);
    return `<i data-week="${wi}" data-day="${di}" data-level="${level}" data-count="${count}" data-active="${level>0?1:0}" style="--level:${level};--strength:${(level/4).toFixed(3)};--tone:${tones[level]}" title="${esc(d.date)}${d.date?' — ':''}${count} contributions"></i>`;
  }).join('')}</div>`).join('');
  return `<div class="calendar-shell"><div class="month-axis">${monthAxis}</div><div class="weekday-axis"><span style="--day:1">MON</span><span style="--day:3">WED</span><span style="--day:5">FRI</span></div><div class="calendar-grid">${cells}<b class="calendar-search" aria-hidden="true"><i></i></b></div></div>`
}
function commitStamp(c){
  const date=String(c.date||'');
  const match=String(c.timestamp||'').match(/T(\d{2}):(\d{2})/);
  return match?`${date} · ${match[1]}:${match[2]} UTC`:date;
}
function commitPlan(commits){
  if(!commits.length)return '<div class="activity-empty">No recent public commits available.</div>';
  const count=commits.length;
  const sheets=commits.map((c,i)=>{
    const sequence=count-1-i;
    const index=String(i+1).padStart(2,'0');
    return `<a class="commit-reader-sheet" href="${esc(c.url||'#')}" data-commit="${i}" data-sequence="${sequence}">
      <span class="reader-eyebrow"><b>${i===0?'HEAD':'RECENT '+index}</b><em>${esc(commitStamp(c))}</em></span>
      <span class="reader-copy"><span class="reader-repo">${esc(c.repo)}</span><span class="reader-message">${esc(c.message)}</span></span>
      <span class="reader-foot"><code>${esc(c.sha)}</code><i>OPEN COMMIT ↗</i></span>
    </a>`;
  }).join('');
  const tabs=commits.map((c,i)=>`<span class="commit-reader-tab" data-tab="${i}"><b>${String(i+1).padStart(2,'0')}</b><em>${esc(c.repo)}</em></span>`).join('');
  return `<div class="commit-reader" style="--commit-count:${count}">
    <div class="commit-reader-stage">${sheets}<span class="reader-shutter" aria-hidden="true"></span></div>
    <div class="commit-reader-index">${tabs}<span class="reader-index-line" aria-hidden="true"></span></div>
  </div>`;
}
function activityAscii(){
  const chars=' ·.:;=+*#01';
  const rows=[];
  for(let r=0;r<18;r++){
    let line='';
    for(let c=0;c<176;c++){
      const wave=Math.sin(c*.125+r*.73)+Math.cos(c*.047-r*.91)+Math.sin((c+r*5)*.025)*.8;
      const ridge=Math.abs(Math.sin(c*.035+r*.41));
      const energy=Math.max(0,Math.min(1,(wave+2.8)/5.6))*(.34+ridge*.66);
      const idx=Math.max(0,Math.min(chars.length-1,Math.floor(Math.pow(energy,.72)*(chars.length-1))));
      line+=chars[idx];
    }
    rows.push(`<span class="ascii-line" style="--row:${r};--dir:${r%2?1:-1}">${line}</span>`);
  }
  return `<div class="activity-ascii" aria-hidden="true">${rows.join('')}</div>`;
}
function activity(){
  const a=RT.account||{}, commits=(RT.recent_commits||[]).slice(0,3);
  return `<section class="activity capture" data-capture="activity">
    ${activityAscii()}
    <div class="activity-title"><span>ACTIVITY / 12M</span><h2>Development trace.</h2></div>
    <div class="activity-stats"><div><b>${fmt(a.commits)}</b><span>${esc(a.commits_label||'COMMITS')}</span></div><div><b>${fmt(a.contributions_12m)}</b><span>CONTRIBUTIONS / 12M</span></div><div><b>${fmt(a.active_days_12m)}</b><span>ACTIVE DAYS / 12M</span></div></div>
    <div class="activity-body"><section class="calendar-panel"><div class="panel-kicker"><span>CONTRIBUTION FIELD</span><em>REAL GITHUB DATA</em></div>${calendarMarkup()}<div class="calendar-footer"><span>${fmt(a.active_days_12m)} active days</span><span class="legend">LESS <i style="--level:0"></i><i style="--level:1"></i><i style="--level:2"></i><i style="--level:3"></i><i style="--level:4"></i> MORE</span></div></section><section class="commit-panel"><div class="panel-kicker commit-kicker"><span>RECENT COMMITS</span><em>${String(commits.length).padStart(2,'0')} LATEST</em></div>${commitPlan(commits)}</section></div>
  </section>`
}
$('#app').innerHTML=hero()+stats()+(RT.projects||[]).slice(0,3).map(project).join('')+activity();

let frameT=.42, ctaT=.2;
function ease(x){return 1-Math.pow(1-clamp(x),3)}
function smoothstep(x){x=clamp(x);return x*x*(3-2*x)}
function bezierEaseInOut(x){
  // CSS/Motion easeInOut: cubic-bezier(0.42, 0, 0.58, 1).
  // Newton iteration solves x(u), then evaluates y(u).
  x=clamp(x); if(x===0||x===1)return x;
  const x1=.42,y1=0,x2=.58,y2=1;
  const sample=(u,a,b)=>3*(1-u)*(1-u)*u*a+3*(1-u)*u*u*b+u*u*u;
  const deriv=(u,a,b)=>3*(1-u)*(1-u)*a+6*(1-u)*u*(b-a)+3*u*u*(1-b);
  let u=x;
  for(let i=0;i<6;i++){const dx=sample(u,x1,x2)-x,d=deriv(u,x1,x2);if(Math.abs(d)<1e-6)break;u=clamp(u-dx/d)}
  return sample(u,y1,y2);
}
function heroTimeline(){
  const lines=$$('.console-line');
  const chars=lines.reduce((n,line)=>n+(line.dataset.text||'').length,0);
  const pause=HERO_LINE_PAUSE*Math.max(0,lines.length-1);
  const headlineEnd=Math.max(.8*APPLE_SPEED,.7*APPLE_SPEED+2.8*APPLE_SPEED);
  const resolveStart=headlineEnd+.03;
  const resolveDuration=.36;
  const consoleStart=resolveStart+resolveDuration+.10;
  const typeSeconds=chars/HERO_CHAR_RATE+pause;
  const fadeStart=consoleStart+typeSeconds+.45;
  const fadeDuration=.32;
  return {headlineEnd,resolveStart,resolveDuration,consoleStart,fadeStart,fadeDuration,total:fadeStart+fadeDuration};
}
function setHero(t){
  document.documentElement.style.setProperty('--hero-t',t);
  const timeline=heroTimeline();
  const sec=clamp(t)*timeline.total;
  const loopOpacity=1-smoothstep((sec-timeline.fadeStart)/timeline.fadeDuration);
  document.documentElement.style.setProperty('--hero-loop-opacity',loopOpacity.toFixed(6));
  const rows=$$('.hello-row');

  rows.forEach((row,ri)=>{
    const glyphs=$$('.hello-glyph-path',row), fill=$('.hello-line-fill',row);
    if(glyphs.length){
      const delay=ri===0 ? 0 : .7*APPLE_SPEED;
      const duration=ri===0 ? .8*APPLE_SPEED : 2.8*APPLE_SPEED;
      const draw=bezierEaseInOut((sec-delay)/duration);

      // Use the exact two-path Apple timing, but distribute each path's
      // pathLength progression across our glyphs in reading order. This avoids
      // the previous "all outlines appear together" look and gives the phrase
      // a real left-to-right writing motion.
      const lengths=glyphs.map(g=>{
        const cached=Number(g.dataset.length||0);
        if(cached>0) return cached;
        const len=Math.max(1,g.getTotalLength());
        g.dataset.length=String(len);
        return len;
      });
      const total=lengths.reduce((a,b)=>a+b,0);
      const travelled=draw*total;
      let offset=0;

      glyphs.forEach((g,gi)=>{
        const local=clamp((travelled-offset)/lengths[gi]);
        g.style.setProperty('--glyph-draw',local.toFixed(6));
        g.style.setProperty('--stroke',local>0?1:0);
        offset+=lengths[gi];
      });

      // Simple monotonic crossfade: the filled word begins resolving first,
      // then the writing stroke fades a fraction later. No bounce/translation.
      const fillIn=bezierEaseInOut((sec-timeline.resolveStart)/timeline.resolveDuration);
      const strokeFade=bezierEaseInOut((sec-(timeline.resolveStart+.055))/(timeline.resolveDuration*.92));

      glyphs.forEach(g=>{
        const localStroke=Number(g.style.getPropertyValue('--stroke'))||0;
        g.style.setProperty('--stroke-alpha',(localStroke?Math.max(0,1-strokeFade):0).toFixed(6));
      });

      row.style.setProperty('--resolve',fillIn.toFixed(6));
      if(fill) fill.style.setProperty('--fill-alpha',fillIn.toFixed(6));
    }else{
      const chars=$$('.hello-char',row);
      const start=.04+ri*.17, end=.31+ri*.20;
      const head=smoothstep((t-start)/(end-start))*chars.length;
      chars.forEach((e,i)=>e.style.setProperty('--ink',clamp(head-i).toFixed(4)));
    }
  });

  const lines=$$('.console-line');
  let cursorSec=timeline.consoleStart;
  lines.forEach((line,li)=>{
    const text=line.dataset.text||'';
    const local=Math.max(0,sec-cursorSec);
    const typedCount=Math.max(0,Math.min(text.length,Math.floor(local*HERO_CHAR_RATE+1e-9)));
    const typed=$('.typed',line);
    if(typed) typed.textContent=text.slice(0,typedCount);

    const lineDuration=text.length/HERO_CHAR_RATE;
    const active=sec>=cursorSec && sec<cursorSec+lineDuration;
    const done=sec>=cursorSec+lineDuration;

    line.style.setProperty('--line-on',(active||done)?1:0);
    line.style.setProperty('--cursor-on',active?1:0);
    line.style.setProperty('--cursor-alpha',active?.82:0);

    cursorSec += lineDuration + (li<lines.length-1 ? HERO_LINE_PAUSE : 0);
  });
}
function setStats(t){const drift=Math.sin(t*Math.PI*2)*26;document.documentElement.style.setProperty('--marquee-x',drift.toFixed(3)+'px')}
function setProject(slug,t){const sec=document.querySelector(`[data-slug="${CSS.escape(slug)}"]`); if(!sec)return; sec.style.setProperty('--pt',t); const cards=$$('.media-card',sec); if(cards.length){const phase=(t*cards.length)%cards.length,active=Math.floor(phase); cards.forEach((c,i)=>{let pos=(i-active+cards.length)%cards.length;c.style.setProperty('--pos',pos);c.style.setProperty('--frac',phase-active)})}}
function setActivity(t){
  const sec=$('.activity'); if(!sec)return;
  const tt=clamp(t); sec.style.setProperty('--at',tt);

  $$('.ascii-line',sec).forEach((line,i)=>{
    const drift=Math.sin(tt*Math.PI*2+i*.63)*8+Math.sin(tt*Math.PI*4+i*.21)*3;
    const rise=Math.sin(tt*Math.PI*2+i*.37)*1.8;
    line.style.transform=`translate3d(${drift.toFixed(2)}px,${rise.toFixed(2)}px,0)`;
    line.style.opacity=String(.045+Math.max(0,Math.sin(tt*Math.PI*2+i*.52))*.04);
  });

  // Data-lock reveal. Every cell is searched, but only the real GitHub level
  // survives the scan. Higher real levels produce a stronger confirmation and
  // settle to their exact final tone; zero-level cells return to graphite.
  const search=smoothstep((tt-.035)/.60);
  const reset=smoothstep((tt-.94)/.04);
  const hold=1-reset;
  const weeks=$$('.contrib-week',sec), weekCount=Math.max(1,weeks.length-1);
  sec.style.setProperty('--grid-head',(-5+search*111).toFixed(3)+'%');
  sec.style.setProperty('--grid-reset',reset.toFixed(5));

  weeks.forEach((w,wi)=>{
    let weekEnergy=0;
    $$('i',w).forEach((cell,di)=>{
      const level=Math.max(0,Math.min(4,Number(cell.dataset.level)||0));
      const count=Math.max(0,Number(cell.dataset.count)||0);
      const strength=level/4;
      const seed=((wi*19+di*37+count*3)%17)-8;
      const jitter=seed*.0022+(di-3)*.0012;
      const threshold=clamp((wi/weekCount)*.92+jitter);
      const local=clamp((search-threshold)/.078);
      const enter=smoothstep(local/.24);
      const leave=1-smoothstep((local-.38)/.62);
      const discovery=enter*leave*(.56+strength*.44)*hold;
      const resolved=smoothstep((local-.24)/.66)*hold;
      const confirm=smoothstep((local-.43)/.27)*strength*hold;

      cell.style.setProperty('--discovery',discovery.toFixed(5));
      cell.style.setProperty('--resolved',resolved.toFixed(5));
      cell.style.setProperty('--confirm',confirm.toFixed(5));
      weekEnergy=Math.max(weekEnergy,discovery+confirm*.28);
    });
    w.style.setProperty('--week-energy',weekEnergy.toFixed(5));
  });

  // Commit reader cycle. The loop begins and ends on HEAD, so the GIF wraps
  // without a reverse jump. A brief closed-page transition hides the reset to
  // the oldest record, then each record receives a deliberate reading hold.
  const reader=$('.commit-reader',sec);
  const sheets=$$('.commit-reader-sheet',sec), tabs=$$('.commit-reader-tab',sec);
  const count=Math.max(1,sheets.length);
  const oldest=count-1;
  const middle=Math.max(0,count-2);
  let cursor=0, readerVisibility=1, chapterReveal=1;

  if(count>1){
    if(tt<.10){
      cursor=0;
    }else if(tt<.17){
      const q=smoothstep((tt-.10)/.07);
      cursor=0; readerVisibility=1-q; chapterReveal=1;
    }else if(tt<.20){
      cursor=oldest; readerVisibility=0; chapterReveal=0;
    }else if(tt<.29){
      const q=smoothstep((tt-.20)/.09);
      cursor=oldest; readerVisibility=q; chapterReveal=q;
    }else if(count===2){
      if(tt<.58){
        cursor=oldest;
      }else if(tt<.72){
        const q=bezierEaseInOut((tt-.58)/.14);
        cursor=oldest*(1-q); chapterReveal=.82+.18*Math.sin(q*Math.PI);
      }else{
        cursor=0;
      }
    }else{
      if(tt<.47){
        cursor=oldest;
      }else if(tt<.58){
        const q=bezierEaseInOut((tt-.47)/.11);
        cursor=oldest+(middle-oldest)*q; chapterReveal=.82+.18*Math.sin(q*Math.PI);
      }else if(tt<.70){
        cursor=middle;
      }else if(tt<.82){
        const q=bezierEaseInOut((tt-.70)/.12);
        cursor=middle*(1-q); chapterReveal=.82+.18*Math.sin(q*Math.PI);
      }else{
        cursor=0;
      }
    }
  }

  if(reader){
    reader.style.setProperty('--reader-cursor',cursor.toFixed(5));
    reader.style.setProperty('--reader-visibility',readerVisibility.toFixed(5));
    reader.style.setProperty('--reader-reveal',chapterReveal.toFixed(5));
  }

  const readerClosing=tt>=.10&&tt<.17;
  sheets.forEach((sheet,i)=>{
    const distance=Math.abs(i-cursor);
    const focus=smoothstep(clamp(1-distance))*readerVisibility;
    const direction=i-cursor;
    const reveal=(readerClosing&&i===0)?1:smoothstep((focus-.08)/.78)*chapterReveal;
    sheet.style.setProperty('--focus',focus.toFixed(5));
    sheet.style.setProperty('--offset',(direction*11).toFixed(3)+'px');
    sheet.style.setProperty('--settle',reveal.toFixed(5));
  });
  tabs.forEach((tab,i)=>{
    const focus=smoothstep(clamp(1-Math.abs(i-cursor)))*readerVisibility;
    tab.style.setProperty('--tab-focus',focus.toFixed(5));
  });
}
window.__THOTH_RENDER_CTA=t=>{ctaT=t;document.documentElement.style.setProperty('--cta-t',t)};
window.__THOTH_RENDER_FRAME=(scene,t)=>{frameT=t;if(scene==='hero'||scene==='all')setHero(t);if(scene==='stats'||scene==='all')setStats(t);if(scene.startsWith('project-'))setProject(scene.slice(8),t);if(scene==='all')(RT.projects||[]).forEach(p=>setProject(p.slug,t));if(scene==='activity'||scene==='all')setActivity(t);window.__THOTH_RENDER_CTA(t)};
window.__THOTH_RENDER_FRAME('all',.42);
