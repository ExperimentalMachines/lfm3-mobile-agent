"""Bounded, auditable public-source downloads for the dataset review."""
import concurrent.futures, hashlib, json, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
LEDGER = ROOT / 'downloads.jsonl'
CAP = 490_000_000

def fetch(item):
    name, url, *limit = item
    maximum = limit[0] if limit else 8_000_000
    range_args = ['--range',limit[1]] if len(limit)>1 else []
    target = ROOT / name
    if target.exists():
        return {'name':name, 'cached':True, 'bytes':target.stat().st_size}
    target.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(['curl','--location','--fail','--silent','--show-error',
        '--max-time','90','--max-filesize',str(maximum),
        '--output',str(target),'--write-out','%{http_code} %{size_download}',*range_args,url],
        capture_output=True, text=True)
    size = target.stat().st_size if target.exists() else 0
    result = dict(name=name,url=url,bytes=size,status=proc.returncode,http=proc.stdout,
                  error=proc.stderr[:400],time=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    if size:
        result['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    return result

if __name__ == '__main__':
    items=json.loads(sys.stdin.read())
    used=sum(json.loads(s).get('bytes',0) for s in LEDGER.read_text().splitlines()) if LEDGER.exists() else 0
    worst=sum(i[2] if len(i)>2 else 8_000_000 for i in items if not (ROOT/i[0]).exists())
    if used+worst>CAP:
        raise SystemExit(f'Refusing batch: used={used}, batch maxima={worst}, cap={CAP}')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(fetch,items))
    with LEDGER.open('a') as f:
        for result in results:
            if not result.get('cached'): f.write(json.dumps(result)+'\n')
            print(json.dumps(result))
