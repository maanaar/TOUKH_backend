import json
import urllib.request, http.cookiejar

DB = 'SayCare'
USER = 'admin'
PASS = 'admin'
BASE = 'http://localhost:8019'

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def rpc(path, payload):
    data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': payload}).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={'Content-Type': 'application/json'})
    return opener.open(req).read()

rpc('/web/session/authenticate', {'db': DB, 'login': USER, 'password': PASS})

def get(path):
    req = urllib.request.Request(BASE + path)
    return json.loads(opener.open(req).read())

specialties = get('/saycare/api/specialties')
result = []
for s in specialties:
    services = get(f'/saycare/api/services?specialty_id={s["id"]}')
    result.append({
        'id': s['id'],
        'name': s['name'],
        'code': s.get('code', ''),
        'services': [{'id': sv['id'], 'name': sv['name'], 'price': sv.get('price')} for sv in services],
    })

print(json.dumps(result, ensure_ascii=False, indent=2))
