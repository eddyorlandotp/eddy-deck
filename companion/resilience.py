"""Self-healing that keeps one Eddy Deck identity reachable.

Observed failure (beta 11): an antivirus quarantined the installed EddyDeck.exe.
The Desktop shortcut had been written through WScript.Shell, which stores
link-tracking data. With its target missing, Windows resolved it to an older
``EddyDeck-previous-*`` copy with another data folder and TLS identity, so
Android correctly refused it. This module:

* writes shortcuts without link tracking, so they never drift to other copies;
* renames the executable inside rollback copies (the verified ZIPs in
  ``recovery`` remain the rollback source);
* keeps the user's "start with Windows" choice outside the shortcut itself;
* registers a per-user watchdog task that runs the independent checker;
* records an intentional exit so the watchdog never reopens a closed app.

Nothing here elevates, reinstalls silently or touches antivirus settings.
"""
import ctypes, datetime as dt, json, logging, os, re, sys, time
from pathlib import Path

APP_NAME = 'Eddy Deck'
EXE = 'EddyDeck.exe'
DISABLED_SUFFIX = '.anterior'
TASK_NAME = 'Eddy Deck - Vigilante'
WATCH_INTERVAL = 'PT5M'
# SHELL_LINK_DATA_FLAGS: SLDF_FORCE_NO_LINKTRACK | SLDF_DISABLE_LINK_PATH_TRACKING
# | SLDF_DISABLE_KNOWNFOLDER_RELATIVE_TRACKING.
NO_TRACKING = 0x40000 | 0x100000 | 0x200000
log = logging.getLogger(__name__)

def programs_root():
    return Path(os.environ['LOCALAPPDATA']) / 'Programs'

def canonical_dir():
    return programs_root() / 'EddyDeck'

def canonical_exe():
    return canonical_dir() / EXE

def start_menu():
    return Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'

def startup_link():
    return start_menu() / 'Startup' / (APP_NAME + '.lnk')

def menu_link():
    return start_menu() / (APP_NAME + '.lnk')

def desktop_link():
    try:
        from win32com.shell import shell, shellcon
        folder = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0)
    except Exception:
        folder = str(Path(os.environ['USERPROFILE']) / 'Desktop')
    return Path(folder) / (APP_NAME + '.lnk')

# ---------------------------------------------------------------- versions
_VERSION = re.compile(r'^(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})(?:-(alpha|beta|rc)\.([1-9][0-9]{0,5}))?$')

def version_key(value):
    """Same ordering as GitHubUpdate.VersionParts in the C# checker."""
    m = _VERSION.match(value or '')
    if not m:
        raise ValueError('Versión de Eddy Deck inválida.')
    stage = ('alpha', 'beta', 'rc').index(m.group(4)) if m.group(4) else 3
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), stage, int(m.group(5) or 0))

def installed_version(folder=None):
    """Version declared by an installed folder, or None if unreadable."""
    try:
        manifest = json.loads(((folder or canonical_dir()) / 'release-manifest.json').read_text(encoding='utf-8'))
        version = manifest.get('version')
        version_key(version)
        return version
    except (OSError, ValueError, TypeError, AttributeError):
        return None

def superseded_by(running_exe, own_version):
    """Return the canonical version when this copy is an older, non-canonical one.

    Only the installed folder is trusted as the reference; an extracted package
    elsewhere may still run if it is not older (for example before installing).
    """
    try:
        running = Path(running_exe).resolve()
        if running.parent == canonical_dir().resolve():
            return None
        if not canonical_exe().is_file():
            return None
        other = installed_version()
        if other and version_key(other) > version_key(own_version):
            return other
    except (OSError, ValueError, KeyError):
        return None
    return None

# --------------------------------------------------------------- shortcuts
def _com():
    import pythoncom
    pythoncom.CoInitialize()
    return pythoncom

def write_shortcut(path, target, arguments='', description=''):
    """Create a fresh .lnk without link tracking. Replaces the file atomically."""
    pythoncom = _com()
    try:
        from win32com.shell import shell
        path = Path(path); target = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        link.SetPath(str(target))
        link.SetArguments(arguments)
        link.SetWorkingDirectory(str(target.parent))
        link.SetIconLocation(str(target), 0)
        if description:
            link.SetDescription(description)
        data = link.QueryInterface(shell.IID_IShellLinkDataList)
        data.SetFlags(data.GetFlags() | NO_TRACKING)
        temp = path.with_name(path.stem + '.nuevo.lnk')
        link.QueryInterface(pythoncom.IID_IPersistFile).Save(str(temp), 0)
        os.replace(temp, path)
    finally:
        pythoncom.CoUninitialize()

def read_shortcut(path):
    """Return (target, arguments, flags) as stored. Never calls Resolve, which
    could search for and silently pick another copy."""
    pythoncom = _com()
    try:
        from win32com.shell import shell
        link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        link.QueryInterface(pythoncom.IID_IPersistFile).Load(str(path))
        target = link.GetPath(4)[0]  # SLGP_RAWPATH
        flags = link.QueryInterface(shell.IID_IShellLinkDataList).GetFlags()
        return target, link.GetArguments(), flags
    finally:
        pythoncom.CoUninitialize()

def shortcut_ok(path, target, arguments=''):
    try:
        stored, args, flags = read_shortcut(path)
    except Exception:
        return False
    same = os.path.normcase(os.path.abspath(stored)) == os.path.normcase(os.path.abspath(str(target)))
    return same and args.strip() == arguments and flags & NO_TRACKING == NO_TRACKING

# ------------------------------------------------------------- preferences
def _prefs_file(data):
    return Path(data) / 'preferences.json'

def read_preferences(data):
    try:
        value = json.loads(_prefs_file(data).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def write_preferences(data, **changes):
    from companion.core import atomic_json
    prefs = read_preferences(data); prefs.update(changes)
    atomic_json(_prefs_file(data), prefs)
    return prefs

def startup_wanted(data):
    """The choice survives an antivirus deleting the Startup shortcut.
    Before this release the shortcut itself was the only record, so a missing
    preference is inferred once from it."""
    prefs = read_preferences(data)
    if isinstance(prefs.get('startup'), bool):
        return prefs['startup']
    wanted = startup_link().exists()
    try:
        write_preferences(data, startup=wanted)
    except OSError:
        pass
    return wanted

# --------------------------------------------------------- intentional exit
def _boot_time():
    k = ctypes.windll.kernel32
    k.GetTickCount64.restype = ctypes.c_ulonglong
    return time.time() - k.GetTickCount64() / 1000.0

def mark_user_exit(data):
    from companion.core import atomic_json
    try:
        atomic_json(Path(data) / 'user-exit.json', {'at': time.time(), 'reason': 'Salir'})
    except OSError:
        log.warning('No se pudo registrar la salida intencional.')

def clear_user_exit(data):
    try:
        (Path(data) / 'user-exit.json').unlink(missing_ok=True)
    except OSError:
        pass

def user_exited(data, boot=None):
    """True only for an exit chosen during the current Windows session."""
    try:
        at = float(json.loads((Path(data) / 'user-exit.json').read_text(encoding='utf-8'))['at'])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return at >= (boot if boot is not None else _boot_time()) - 5

# ----------------------------------------------------------- rollback copies
def disable_stale_copies(root=None):
    """Rename EddyDeck.exe inside EddyDeck-previous-* so no shortcut, search or
    double click can start an older identity. Files and folders are kept."""
    root = Path(root or programs_root())
    changed = []
    try:
        folders = [p for p in root.iterdir() if p.is_dir() and p.name.startswith('EddyDeck-previous-')]
    except OSError:
        return changed
    for folder in folders:
        exe = folder / EXE
        if not exe.is_file():
            continue
        try:
            os.replace(exe, folder / (EXE + DISABLED_SUFFIX))
            changed.append(folder.name)
        except OSError:
            # A copy that is running keeps its name; the next start retries.
            continue
    return changed

# ------------------------------------------------------------ watchdog task
def checker_path(data):
    from companion.integrity import CHECKER
    return Path(data) / 'Rescue' / CHECKER

def _current_user():
    import win32api
    return win32api.GetUserNameEx(2)  # NameSamCompatible, DOMAIN\user

def register_watchdog(data):
    """Per-user task (no elevation): at logon and every five minutes it runs
    the checker in --watchdog mode. The checker only relaunches the installed
    app or shows a notice; it never reinstalls files by itself."""
    import hashlib
    from companion.integrity import CHECKER
    checker = checker_path(data)
    if not checker.is_file():
        raise FileNotFoundError('Falta el comprobador independiente en Rescue.')
    # An older checker has no --watchdog mode and would open its window every
    # five minutes. Require the exact copy shipped with the installed release.
    installed = canonical_dir() / CHECKER
    if not installed.is_file() or hashlib.sha256(checker.read_bytes()).digest() != hashlib.sha256(installed.read_bytes()).digest():
        raise RuntimeError('El comprobador de Rescue no coincide con la versión instalada.')
    pythoncom = _com()
    try:
        import win32com.client
        service = win32com.client.Dispatch('Schedule.Service'); service.Connect()
        user = _current_user()
        task = service.NewTask(0)
        task.RegistrationInfo.Description = 'Vuelve a abrir Eddy Deck si se cerró por un fallo y avisa si Windows lo bloqueó. No se ejecuta como administrador.'
        task.RegistrationInfo.Author = APP_NAME
        task.Principal.UserId = user
        task.Principal.LogonType = 3        # TASK_LOGON_INTERACTIVE_TOKEN
        task.Principal.RunLevel = 0         # TASK_RUNLEVEL_LUA
        settings = task.Settings
        settings.Enabled = True
        settings.StartWhenAvailable = True
        settings.DisallowStartIfOnBatteries = False
        settings.StopIfGoingOnBatteries = False
        settings.ExecutionTimeLimit = 'PT2M'
        settings.MultipleInstances = 2      # TASK_INSTANCES_IGNORE_NEW
        settings.Priority = 7
        logon = task.Triggers.Create(9)     # TASK_TRIGGER_LOGON
        logon.UserId = user
        logon.Delay = 'PT1M'
        logon.Repetition.Interval = WATCH_INTERVAL
        periodic = task.Triggers.Create(1)  # TASK_TRIGGER_TIME, covers the current session
        periodic.StartBoundary = (dt.datetime.now() + dt.timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%S')
        periodic.Repetition.Interval = WATCH_INTERVAL
        action = task.Actions.Create(0)     # TASK_ACTION_EXEC
        action.Path = str(checker)
        action.Arguments = '--watchdog'
        action.WorkingDirectory = str(checker.parent)
        service.GetFolder('\\').RegisterTaskDefinition(TASK_NAME, task, 6, None, None, 3)
    finally:
        pythoncom.CoUninitialize()

def watchdog_state(data):
    """'missing', 'ok', 'disabled' (a person turned it off: respected) or 'different'."""
    pythoncom = _com()
    try:
        import win32com.client
        service = win32com.client.Dispatch('Schedule.Service'); service.Connect()
        try:
            task = service.GetFolder('\\').GetTask(TASK_NAME)
        except Exception:
            return 'missing'
        actions = task.Definition.Actions
        if not (actions.Count == 1 and os.path.normcase(actions.Item(1).Path) == os.path.normcase(str(checker_path(data)))):
            return 'different'
        return 'ok' if task.Enabled else 'disabled'
    finally:
        pythoncom.CoUninitialize()

def unregister_watchdog():
    pythoncom = _com()
    try:
        import win32com.client
        service = win32com.client.Dispatch('Schedule.Service'); service.Connect()
        try:
            service.GetFolder('\\').DeleteTask(TASK_NAME, 0)
        except Exception:
            pass
    finally:
        pythoncom.CoUninitialize()

# ------------------------------------------------------------------ startup
def set_startup(data, enabled):
    """Single place for the user's choice: preference, shortcut and watchdog."""
    write_preferences(data, startup=bool(enabled))
    if enabled:
        write_shortcut(startup_link(), canonical_exe(), '--tray', 'Inicia Eddy Deck junto al reloj.')
        try:
            register_watchdog(data)
        except Exception as exc:
            log.warning('No se pudo registrar el vigilante: %s', exc)
    else:
        startup_link().unlink(missing_ok=True)
        unregister_watchdog()

def is_canonical_process():
    return getattr(sys, 'frozen', False) and Path(sys.executable).resolve().parent == canonical_dir().resolve()

def ensure(data, record=None):
    """Run at every start of the installed receiver. Each step is independent:
    a failure is logged and never stops the receiver."""
    results = {}
    def step(name, action):
        try:
            results[name] = action()
        except Exception as exc:
            results[name] = 'error: ' + str(exc)[:160]
            log.warning('Autorreparación %s falló: %s', name, exc)
    exe = canonical_exe()
    description = 'Controla tu PC desde Android, sin IA ni suscripciones.'
    def menu():
        if shortcut_ok(menu_link(), exe):
            return 'ok'
        write_shortcut(menu_link(), exe, '', description); return 'repaired'
    def desktop():
        link = desktop_link()
        # Respect a deleted Desktop shortcut; only correct an existing one.
        if not link.exists():
            return 'absent'
        if shortcut_ok(link, exe):
            return 'ok'
        write_shortcut(link, exe, '', description); return 'repaired'
    def startup():
        if not startup_wanted(data):
            return 'disabled'
        state = 'ok'
        if not shortcut_ok(startup_link(), exe, '--tray'):
            write_shortcut(startup_link(), exe, '--tray', 'Inicia Eddy Deck junto al reloj.'); state = 'repaired'
        watch = watchdog_state(data)
        if watch in ('missing', 'different'):
            register_watchdog(data); state = 'repaired'
        elif watch == 'disabled':
            state = 'watchdog-disabled-by-user' if state == 'ok' else state
        return state
    step('menu', menu)
    step('desktop', desktop)
    step('startup', startup)
    step('staleCopies', lambda: len(disable_stale_copies()))
    if record:
        changed = {k: v for k, v in results.items() if v not in ('ok', 'absent', 'disabled', 'watchdog-disabled-by-user', 0)}
        if changed:
            record(data, 'resilience.ensure', 'repaired', json.dumps(changed, ensure_ascii=False))
    return results
