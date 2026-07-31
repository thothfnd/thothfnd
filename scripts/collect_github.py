from __future__ import annotations
import argparse, os, sys, json, requests, re
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
from common import ROOT, load_json, write_json, slugify, parse_desc_md

API='https://api.github.com'
GRAPHQL='https://api.github.com/graphql'
VERSION='2026-03-10'

class GitHub:
    def __init__(self, token: str | None):
        self.s=requests.Session()
        self.s.headers.update({'Accept':'application/vnd.github+json','X-GitHub-Api-Version':VERSION,'User-Agent':'THOTH-FND-profile-builder'})
        if token: self.s.headers['Authorization']=f'Bearer {token}'
        self.token=token
    def rest(self, path, **params):
        r=self.s.get(API+path, params=params, timeout=30)
        r.raise_for_status(); return r
    def graphql(self, query, variables):
        if not self.token:
            raise RuntimeError('GraphQL pinned-project collection requires GITHUB_TOKEN or GH_TOKEN.')
        r=self.s.post(GRAPHQL,json={'query':query,'variables':variables},timeout=30)
        r.raise_for_status(); payload=r.json()
        if payload.get('errors'): raise RuntimeError(str(payload['errors']))
        return payload['data']

QUERY="""query($login:String!){
 user(login:$login){
  login followers{totalCount}
  pinnedItems(first:10,types:[REPOSITORY]){nodes{... on Repository{name nameWithOwner url description updatedAt isPrivate primaryLanguage{name} owner{login}}}}
  contributionsCollection{totalCommitContributions contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}
 }
}"""
LEVEL={'NONE':0,'FIRST_QUARTILE':1,'SECOND_QUARTILE':2,'THIRD_QUARTILE':3,'FOURTH_QUARTILE':4}

def count_pages(r):
    # For per_page=1, the last page number is the count; no Link => 0/1 based on body length.
    link=r.headers.get('Link','')
    m=re.search(r'[?&]page=(\d+)>; rel="last"',link)
    if m: return int(m.group(1))
    try: body=r.json()
    except Exception: return 0
    return len(body) if isinstance(body,list) else 0

def get_repo_file(gh, full, path):
    try:
        r=gh.rest(f'/repos/{full}/contents/{quote(path)}')
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404: return None
        raise
    j=r.json()
    if j.get('encoding')=='base64' and j.get('content'):
        import base64
        return base64.b64decode(j['content']).decode('utf-8',errors='replace')
    return None

def download_repo_asset(gh, full, path, dest):
    try:
        r=gh.rest(f'/repos/{full}/contents/{quote(path)}')
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code==404: return False
        raise
    j=r.json(); url=j.get('download_url')
    if not url: return False
    data=gh.s.get(url,timeout=30); data.raise_for_status()
    dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data.content); return True

def collect(username, token):
    cfg=load_json(ROOT/'data/profile.json'); gh=GitHub(token)
    data=gh.graphql(QUERY,{'login':username})['user']
    if not data: raise RuntimeError(f'GitHub user not found: {username}')
    pins=[x for x in data['pinnedItems']['nodes'] if x and not x.get('isPrivate')][:int(cfg.get('max_pinned_projects',3))]
    # Public owned repos provide deterministic accessible release/commit aggregation.
    repos=[]; page=1
    while page<=5:
        batch=gh.rest(f'/users/{username}/repos',per_page=100,page=page,type='owner',sort='updated').json()
        repos.extend([x for x in batch if not x.get('fork') and not x.get('private')])
        if len(batch)<100: break
        page+=1
    total_releases=0; public_commits=0; recent=[]
    for repo in repos:
        full=repo['full_name']
        try: total_releases += count_pages(gh.rest(f'/repos/{full}/releases',per_page=1,page=1))
        except requests.HTTPError: pass
        try: public_commits += count_pages(gh.rest(f'/repos/{full}/commits',per_page=1,page=1,author=username))
        except requests.HTTPError: pass
        try:
            rs=gh.rest(f'/repos/{full}/commits',per_page=3,page=1,author=username).json()
            for c in rs:
                dt=((c.get('commit') or {}).get('author') or {}).get('date')
                if not dt: continue
                recent.append({'date':dt[:10],'timestamp':dt,'repo':repo['name'],'sha':c['sha'][:7],'message':((c.get('commit') or {}).get('message') or '').splitlines()[0][:110],'url':c.get('html_url','')})
        except requests.HTTPError: pass
    recent=sorted({c['sha']:c for c in recent}.values(),key=lambda x:x['timestamp'],reverse=True)[:5]
    weeks=data['contributionsCollection']['contributionCalendar']['weeks']
    days=[d for w in weeks for d in w['contributionDays']]
    active=sum(1 for d in days if d['contributionCount']>0)
    levels=[LEVEL.get(d['contributionLevel'],0) for d in days]
    projects=[]
    media_exts=('png','webp','jpg','jpeg')
    base=cfg.get('project_profile_path','.github/profile').rstrip('/')
    for p in pins:
        slug=slugify(p['name']); fallback=cfg.get('fallback_projects',{}).get(slug,{})
        md=get_repo_file(gh,p['nameWithOwner'],f'{base}/desc.md')
        editor=parse_desc_md(md) if md else {}
        pj=get_repo_file(gh,p['nameWithOwner'],f'{base}/profile.json')
        try: meta=json.loads(pj) if pj else {}
        except json.JSONDecodeError: meta={}
        links=meta.get('links') if isinstance(meta.get('links'),list) else []
        links=[x for x in links if isinstance(x,dict) and x.get('url') and x.get('label')]
        if not any(x['label'].lower()=='repository' for x in links): links.insert(0,{'label':'Repository','url':p['url']})
        media=[]; outdir=ROOT/'assets/project-source'/slug
        # logo
        logo=None
        for name in ['logo.png','logo.webp','icon.png','logo.jpg']:
            dest=outdir/name
            if download_repo_asset(gh,p['nameWithOwner'],f'{base}/{name}',dest): logo=str(dest.relative_to(ROOT)).replace('\\','/'); break
        for idx in range(1,6):
            found=False
            for ext in media_exts:
                name=f'cover-{idx:02d}.{ext}'; dest=outdir/name
                if download_repo_asset(gh,p['nameWithOwner'],f'{base}/{name}',dest):
                    media.append({'type':'image','src':'../'+str(dest.relative_to(ROOT)).replace('\\','/'),'label':f'View {idx:02d}'})
                    found=True; break
            if not found and idx>3: break
        projects.append({
          'slug':slug,'name':p['name'],'url':p['url'],'status':meta.get('status') or fallback.get('status') or 'Public project',
          'headline':editor.get('headline') or fallback.get('headline') or p.get('description') or '',
          'overview':editor.get('overview') or fallback.get('overview') or p.get('description') or '',
          'pillars':editor.get('pillars') or fallback.get('pillars') or [],
          'language':(p.get('primaryLanguage') or {}).get('name') or '', 'updated':(p.get('updatedAt') or '')[:10], 'links':links,'logo':logo,'media':media
        })
    return {
      'mode':'live','generated_at':None,
      'account':{'login':username,'followers':data['followers']['totalCount'],'commits_label':'PUBLIC COMMITS','commits':public_commits,'releases':total_releases,'contributions_12m':data['contributionsCollection']['contributionCalendar']['totalContributions'],'active_days_12m':active},
      'contribution_levels':levels,'projects':projects,'recent_commits':recent
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--username'); ap.add_argument('--output',default=str(ROOT/'data/runtime.json')); ap.add_argument('--demo',action='store_true'); args=ap.parse_args()
    if args.demo:
        src=load_json(ROOT/'data/sample-runtime.json'); write_json(Path(args.output),src); return
    cfg=load_json(ROOT/'data/profile.json'); username=args.username or cfg['username']; token=os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    try: payload=collect(username,token)
    except Exception as e:
        print(f'COLLECT_ERROR: {e}',file=sys.stderr); raise
    write_json(Path(args.output),payload)
if __name__=='__main__': main()
