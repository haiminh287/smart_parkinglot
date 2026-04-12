import json,re,ssl,socket,base64,os
from urllib import request,error
results={}
def fetch(url,timeout=15):
    req=request.Request(url,headers={"User-Agent":"smoke-tester"})
    try:
        with request.urlopen(req,timeout=timeout) as r:
            return {"ok":True,"status":getattr(r,"status",200),"content_type":r.headers.get("Content-Type",""),"body":r.read()}
    except error.HTTPError as e:
        return {"ok":False,"status":e.code,"content_type":e.headers.get("Content-Type","") if e.headers else "","body":e.read() if hasattr(e,"read") else b""}
    except Exception as ex:
        return {"ok":False,"status":-1,"error":str(ex),"content_type":"","body":b""}
fe=fetch("https://app.ghepdoicaulong.shop")
results["fe_home"]={k:v for k,v in fe.items() if k!="body"}
asset={"asset_found":False,"asset_url":None,"status":None,"ok":False}
if fe.get("status")==200 and fe.get("body"):
    html=fe["body"].decode("utf-8","ignore")
    m=re.findall(r"(?:src|href)=['\"](/assets/[^'\"]+)['\"]",html)
    if m:
        au="https://app.ghepdoicaulong.shop"+m[0]
        ar=fetch(au)
        asset={"asset_found":True,"asset_url":au,"status":ar.get("status"),"ok":ar.get("status")==200,"content_type":ar.get("content_type","")}
results["fe_asset"]=asset
for k,u in [("api_health","https://api.ghepdoicaulong.shop/api/health"),("parking_health","https://api.ghepdoicaulong.shop/api/parking/health/"),("auth_me_unauth","https://api.ghepdoicaulong.shop/api/auth/me")]:
    r=fetch(u); e={x:y for x,y in r.items() if x!="body"}; e["body_snippet"]=r.get("body",b"").decode("utf-8","ignore")[:180]; results[k]=e
ws={"host":"ws.ghepdoicaulong.shop","path":"/ws/parking/","reachable":False,"status_line":None,"error":None}
try:
    raw=socket.create_connection((ws["host"],443),timeout=10); s=ssl.create_default_context().wrap_socket(raw,server_hostname=ws["host"])
    key=base64.b64encode(os.urandom(16)).decode("ascii")
    req=(f"GET {ws['path']} HTTP/1.1\r\nHost: {ws['host']}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
    s.sendall(req.encode("ascii")); line=s.recv(2048).decode("utf-8","ignore").split("\r\n")[0]; ws["status_line"]=line; ws["reachable"]=any(c in line for c in ["101","400","401","403"]); s.close()
except Exception as ex:
    ws["error"]=str(ex)
results["ws_parking"]=ws
print(json.dumps(results,ensure_ascii=False,indent=2))
