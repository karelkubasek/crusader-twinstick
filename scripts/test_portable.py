# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import argparse,json,os,shutil,subprocess,tempfile,time
ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser(description='Exercise a relocated portable release using a private GOG installer.')
parser.add_argument('--installer',type=Path)
args=parser.parse_args()
installers=sorted((ROOT/'installers').glob('setup_crusader_no_remorse_*.exe'))
installer=args.installer.expanduser().resolve() if args.installer else installers[0] if len(installers)==1 else None
if installer is None or not installer.is_file():
 parser.error('Provide --installer or place one No Remorse installer under installers/.')
report={'checks':[]};gui=None;temporary=None;gui_window=None;previous_windows=set()

def check(ok,name,details=None):
 report['checks'].append({'test':name,'passed':bool(ok),'details':details})
 if not ok:raise AssertionError(name)

def wait_until(predicate,timeout=18):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  result=predicate()
  if result:return result
  time.sleep(.1)
 return None

def visible_window(pid):
 global gui_window
 if gui and pid==gui.pid:
  p=subprocess.run(['xdotool','search','--onlyvisible','--name','Crusader'],capture_output=True,text=True)
  windows=set(p.stdout.splitlines())-previous_windows
  if gui_window:return gui_window if gui_window in windows else None
  if len(windows)==1:
   gui_window=windows.pop();return gui_window
  return None
 p=subprocess.run(['xdotool','search','--onlyvisible','--pid',str(pid)],capture_output=True,text=True)
 for window in reversed(p.stdout.splitlines()):
  prop=subprocess.run(['xprop','-id',window,'_NET_WM_PID'],capture_output=True,text=True)
  if prop.returncode==0:return window
 return None

def child_engine(pid):
 p=Path('/proc')/str(pid)/'task'/str(pid)/'children'
 if p.exists():
  for child in p.read_text().split():
   try:
    if (Path('/proc')/child/'comm').read_text().strip().startswith('scummvm'):return int(child)
   except OSError:pass
 return None

def close_window(window):
 subprocess.run(['xdotool','windowactivate','--sync',window],check=True,capture_output=True)
 subprocess.run(['xdotool','key','alt+F4'],check=True,capture_output=True)

try:
 temporary=tempfile.TemporaryDirectory(prefix='portable smoke ',dir=ROOT/'runtime')
 parent=Path(temporary.name)
 app=parent/'first location'
 shutil.copytree(ROOT/'dist/CrusaderTwinStick-linux-x86_64',app,copy_function=os.link)
 home=parent/'fresh home';home.mkdir()
 env={k:v for k,v in os.environ.items() if k in ('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS')}
 env.update(PATH='/usr/bin:/bin',HOME=str(home),LANG='C.UTF-8',SDL_VIDEODRIVER='x11')
 p=subprocess.run([str(app/'start.sh'),'--status'],cwd='/tmp',env=env,capture_output=True,text=True,timeout=20)
 check(p.returncode==1 and not json.loads(p.stdout)['installed'],'clean_bundle_starts_without_installed_game',p.stdout)
 with (ROOT/'runtime/portable-import.log').open('w') as log:
  p=subprocess.run([str(app/'start.sh'),'--install',str(installer)],cwd='/tmp',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
 check(p.returncode==0,'bundled_python_and_tools_import_gog_without_homebrew')
 status=json.loads(subprocess.check_output([str(app/'start.sh'),'--status'],cwd='/tmp',env=env,text=True))
 check(status['installed'] and status['runtime_available'],'installed_game_is_ready',status)
 moved=parent/'moved app with spaces';app.rename(moved);app=moved
 relocated=subprocess.run([str(app/'start.sh'),'--status'],cwd='/tmp',env=env,capture_output=True,text=True,timeout=20)
 check(relocated.returncode==0,'portable_cli_survives_move',relocated.stdout+relocated.stderr)
 check((app/'user-data/installation/artwork/silencer.png').exists(),'portrait_is_extracted_only_after_local_import')
 logfile=(ROOT/'runtime/portable-ui.log').open('w')
 previous_windows=set(subprocess.run(['xdotool','search','--onlyvisible','--name','Crusader'],capture_output=True,text=True).stdout.splitlines())
 gui=subprocess.Popen([str(app/'start.sh')],cwd='/tmp',env=env,stdout=logfile,stderr=subprocess.STDOUT)
 window=wait_until(lambda:visible_window(gui.pid))
 check(window is not None,'bundled_tk_opens_after_folder_move')
 time.sleep(.8)
 subprocess.run(['imlib2_grab','-id',window,str(ROOT/'runtime/portable-ready.png')],check=True,capture_output=True)
 subprocess.run(['xdotool','windowactivate','--sync',window],check=True,capture_output=True)
 subprocess.run(['xdotool','key','--clearmodifiers','space'],check=True,capture_output=True)
 game=wait_until(lambda:child_engine(gui.pid))
 check(game is not None,'home_play_button_starts_bundled_engine_after_relocation')
 game_window=wait_until(lambda:visible_window(game))
 check(game_window is not None,'bundled_engine_has_visible_game_window')
 time.sleep(1)
 game_window=visible_window(game)
 properties=subprocess.check_output(['xprop','-id',game_window,'_NET_WM_STATE'],text=True)
 check('_NET_WM_STATE_FULLSCREEN' in properties,'game_launch_honors_fullscreen')
 close_window(game_window)
 check(wait_until(lambda:child_engine(gui.pid) is None),'game_exits_and_is_reaped')
 window=wait_until(lambda:visible_window(gui.pid))
 check(window is not None,'launcher_returns_to_hub')
 config=(app/'user-data/scummvm.ini').read_text()
 check(str(app/'user-data/installation/game-data') in config and str(app/'runtime-engine/share/themes') in config,
       'relocation_updates_game_and_theme_paths')
 subprocess.run(['xdotool','windowactivate','--sync',window],check=True,capture_output=True)
 # The hub starts with Play focused; Tab selects Controller layout, whose
 # first focus target is the remapper. Exercise the keyboard route as shipped.
 subprocess.run(['xdotool','key','--clearmodifiers','Tab','space'],check=True,capture_output=True)
 time.sleep(.4)
 subprocess.run(['xdotool','key','--clearmodifiers','space'],check=True,capture_output=True)
 remapper=wait_until(lambda:child_engine(gui.pid))
 check(remapper is not None,'existing_remapper_launches_from_portable_app')
 remap_window=wait_until(lambda:visible_window(remapper))
 check(remap_window is not None,'portable_remapper_is_visible')
 time.sleep(.8);close_window(visible_window(remapper))
 check(wait_until(lambda:child_engine(gui.pid) is None),'remapper_exits_cleanly')
 window=wait_until(lambda:visible_window(gui.pid));close_window(window)
 check(gui.wait(timeout=10)==0,'portable_launcher_exits_cleanly')
 report['passed']=True
except Exception as error:
 report['passed']=False;report['error']=str(error)
finally:
 if gui and gui.poll() is None:
  child=child_engine(gui.pid)
  if child:
   try:os.kill(child,15)
   except ProcessLookupError:pass
  gui.terminate()
  try:gui.wait(timeout=3)
  except subprocess.TimeoutExpired:gui.kill();gui.wait()
 if temporary:
  for log in (app/'user-data/logs').glob('*.log'):
   shutil.copy2(log,ROOT/'runtime'/('portable-'+log.name))
  temporary.cleanup()
 (ROOT/'runtime/portable-smoke-results.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
 if not report.get('passed'):raise SystemExit(1)
