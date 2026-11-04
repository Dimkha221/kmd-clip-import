"""KMD CLIP YouTube import prototype. Do not expose publicly without authentication and quotas."""
import os, re, sys, time, shutil, tempfile, subprocess, threading, uuid
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, jsonify, request, send_file, send_from_directory
import imageio_ffmpeg

SITE=Path(__file__).parent/'site'
ROOT=Path(tempfile.mkdtemp(prefix='kmd-import-'))
BIN=ROOT/'bin';BIN.mkdir();(BIN/'ffmpeg').symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
LIMIT=250*1024*1024
ALLOWED_ORIGINS=set(filter(None,os.getenv('ALLOWED_ORIGINS','https://shrill-term-e494.diagnekhadim621.workers.dev').split(',')))
jobs={}; lock=threading.Lock(); attempts=[]
app=Flask(__name__,static_folder=None)

@app.after_request
def cors(response):
 origin=request.headers.get('Origin')
 if origin and origin in ALLOWED_ORIGINS:
  response.headers['Access-Control-Allow-Origin']=origin
  response.headers['Vary']='Origin'
  response.headers['Access-Control-Allow-Methods']='GET, POST, OPTIONS'
  response.headers['Access-Control-Allow-Headers']='Content-Type'
 return response

def valid_url(url):
 try:
  p=urlparse(url); host=(p.hostname or '').lower()
  if p.scheme!='https' or p.username or p.password or p.port not in (None,443):return False
  if host=='youtu.be':return bool(re.fullmatch(r'/[a-zA-Z0-9_-]{11}/?',p.path))
  return host in ('youtube.com','www.youtube.com','m.youtube.com') and (p.path=='/watch' or bool(re.fullmatch(r'/(?:shorts|embed)/[a-zA-Z0-9_-]{11}/?',p.path)))
 except ValueError:return False

def clean():
 now=time.time()
 with lock:
  expired=[k for k,v in jobs.items() if v['state']!='working' and now-v['created']>900]
  for k in expired:
   shutil.rmtree(ROOT/k,ignore_errors=True);jobs.pop(k,None)

def work(id,url):
 job=jobs[id]; out=ROOT/id/'video.mp4'
 cmd=[sys.executable,'-m','yt_dlp','--no-playlist','--no-warnings','--socket-timeout','15','--retries','2','--max-filesize','250M','--ffmpeg-location',str(BIN/'ffmpeg'),'-f','bestvideo[ext=mp4][vcodec^=avc1][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][vcodec!=none][acodec!=none]','--merge-output-format','mp4','-o',str(out),url]
 try:
  p=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=600)
  if p.returncode or not out.is_file():
   detail=p.stderr.lower()
   if 'file is larger' in detail or 'larger than max-filesize' in detail: msg='La vidéo dépasse la limite de 250 Mo.'
   elif 'sign in' in detail or 'bot' in detail: msg='YouTube a bloqué ce serveur. Essayez avec une autre vidéo ou importez un fichier local.'
   else: msg='YouTube n’a pas fourni une vidéo exploitable. Vérifiez que le lien est public, puis réessayez.'
   raise RuntimeError(msg)
  if out.stat().st_size>LIMIT:raise RuntimeError('La vidéo téléchargée dépasse la limite de 250 Mo.')
  job['state']='ready';job['size']=out.stat().st_size
 except subprocess.TimeoutExpired: job.update(state='error',error='Le téléchargement a pris trop de temps.')
 except Exception as e:job.update(state='error',error=str(e))

@app.route('/api/import',methods=['POST','OPTIONS'])
def new():
 if request.method=='OPTIONS':return '',204
 origin=request.headers.get('Origin')
 if origin and origin not in ALLOWED_ORIGINS and urlparse(origin).netloc!=request.host:
  return jsonify(error='Origine non autorisée.'),403
 clean();url=str((request.get_json(silent=True) or {}).get('url','')).strip()
 if not valid_url(url):return jsonify(error='Saisissez un lien HTTPS vers une vidéo YouTube individuelle.'),400
 with lock:
  now=time.time(); attempts[:]=[t for t in attempts if now-t<3600]
  if len(attempts)>=8:return jsonify(error='Limite temporaire atteinte. Réessayez plus tard.'),429
  if sum(j['state']=='working' for j in jobs.values())>=2:return jsonify(error='Le service est occupé. Réessayez dans quelques instants.'),429
  attempts.append(now)
  id=uuid.uuid4().hex;(ROOT/id).mkdir();jobs[id]={'state':'working','created':time.time()}
 threading.Thread(target=work,args=(id,url),daemon=True).start();return jsonify(id=id)

@app.get('/api/import/<id>')
def status(id):
 clean();j=jobs.get(id)
 if not j:return jsonify(error='Import expiré ou introuvable.'),404
 return jsonify({k:v for k,v in j.items() if k in ('state','size','error')})

@app.get('/api/import/<id>/video')
def video(id):
 j=jobs.get(id)
 if not j or j['state']!='ready':return jsonify(error='Vidéo indisponible.'),404
 return send_file(ROOT/id/'video.mp4',mimetype='video/mp4',conditional=True)

@app.get('/health')
def health():return jsonify(status='ok')

@app.get('/')
def index():return send_from_directory(SITE,'index.html')
@app.get('/<path:path>')
def static(path):return send_from_directory(SITE,path)

def clean_forever():
 while True:
  time.sleep(60)
  clean()
threading.Thread(target=clean_forever,daemon=True).start()

if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT','8002')),threaded=True)
