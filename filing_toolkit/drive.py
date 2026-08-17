#!/usr/bin/env python
"""Driver for the ITD e-Filing Mac utility (Wails/WKWebView) via Quartz events.

TOKEN ECONOMY MATTERS HERE. The utility has no DOM you can read, so screenshots
are the only feedback channel — which makes them the single biggest token cost
of a filing. Two features exist to keep that cost small; use them:

  * `shot` downscales to 50% and writes JPEG by DEFAULT (~4x fewer tokens than a
    full-size PNG). Use `--crop` to grab just the region you care about — a
    cropped strip costs a fraction of a full window.
  * `batch` runs a whole sequence of actions in ONE call, so you take ONE
    verification screenshot at the end instead of one per click.

Usage:
  drive.py shot [out.jpg] [--scale 0.5] [--crop X,Y,W,H] [--full]
  drive.py click X Y               - click at window coords
  drive.py dblclick X Y
  drive.py move X Y
  drive.py type "text"             - type text via keyboard events
  drive.py paste "text"            - clear field + clipboard-paste (Angular-safe)
  drive.py key <name>              - return, tab, escape, down, up, cmd+a, delete
  drive.py scroll X Y AMT          - scroll at coords, AMT>0 = down
  drive.py batch 'click 100 200; paste 300 400 "12345"; key return; scroll 0 0 5'

Window is auto-located each call (owner contains 'ITD').
"""
import sys, time, subprocess, shlex
import Quartz

def win():
    wins = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
    for w in wins:
        if 'ITD' in str(w.get('kCGWindowOwnerName','')):
            b = w['kCGWindowBounds']
            return int(w['kCGWindowNumber']), b['X'], b['Y'], b['Width'], b['Height']
    raise SystemExit('ITD window not found — run:\n'
                     '  osascript -e \'tell application id "com.wails.ITDe-Filing-2026" to activate\'')

def to_global(px, py):
    _, X, Y, W, H = win()
    return X + px, Y + py   # non-retina external display: image px == window points

def post_mouse(kind, x, y, btn=Quartz.kCGMouseButtonLeft, clicks=1):
    ev = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), btn)
    Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, clicks)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def focus():
    subprocess.run(['osascript','-e','tell application id "com.wails.ITDe-Filing-2026" to activate'],
                   capture_output=True)
    time.sleep(0.4)

def click(px, py, n=1):
    x, y = to_global(px, py)
    post_mouse(Quartz.kCGEventMouseMoved, x, y)
    time.sleep(0.15)
    for i in range(n):
        post_mouse(Quartz.kCGEventLeftMouseDown, x, y, clicks=i+1)
        time.sleep(0.05)
        post_mouse(Quartz.kCGEventLeftMouseUp, x, y, clicks=i+1)
        time.sleep(0.08)

KEYCODES = {'return':36,'tab':48,'space':49,'delete':51,'escape':53,'left':123,'right':124,'down':125,'up':126,'a':0,'v':9,'c':8,'x':7}
def key(name):
    mods = 0
    if name.startswith('cmd+'):
        mods = Quartz.kCGEventFlagMaskCommand; name = name[4:]
    kc = KEYCODES[name]
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, kc, down)
        if mods: Quartz.CGEventSetFlags(ev, mods)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.03)

def type_text(s):
    for ch in s:
        ev = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
        Quartz.CGEventKeyboardSetUnicodeString(ev, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        ev = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
        Quartz.CGEventKeyboardSetUnicodeString(ev, len(ch), ch)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.02)

def paste(px, py, value):
    """Angular text fields reject synthetic unicode typing — clear + Cmd+V works."""
    click(px, py)                      # click auto-selects the field content
    key('delete')
    subprocess.run(['pbcopy'], input=value.encode(), check=True)
    key('cmd+v')
    time.sleep(0.1)

def scroll(px, py, amt):
    x, y = to_global(px, py)
    post_mouse(Quartz.kCGEventMouseMoved, x, y)
    time.sleep(0.1)
    ev = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitLine, 1, -int(amt))
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)

def shot(out='/tmp/itd.jpg', scale=0.5, crop=None):
    """Capture the utility window. Downscaled JPEG by default to save tokens.
    crop = (x, y, w, h) in window coords — prefer it when you only need one panel."""
    wid = win()[0]
    raw = '/tmp/_itd_raw.png'
    subprocess.run(['screencapture','-x','-o','-l',str(wid),raw], check=True)
    # sips ships with macOS — no extra dependency needed for resize/convert/crop
    if crop:
        x, y, w, h = crop
        subprocess.run(['sips','--cropOffset',str(y),str(x),'-c',str(h),str(w),raw,'--out',raw],
                       capture_output=True)
    args = ['sips','-s','format','jpeg','-s','formatOptions','60']
    if scale and scale != 1:
        info = subprocess.run(['sips','-g','pixelWidth',raw], capture_output=True, text=True).stdout
        width = int(info.strip().split(':')[-1])
        args += ['-Z', str(int(width * scale))]
    subprocess.run(args + [raw, '--out', out], capture_output=True, check=True)
    print(out)

def run_action(parts):
    """Execute one action from a batch string."""
    c = parts[0]
    if c == 'click':    click(int(parts[1]), int(parts[2]))
    elif c == 'dblclick': click(int(parts[1]), int(parts[2]), n=2)
    elif c == 'paste':  paste(int(parts[1]), int(parts[2]), parts[3])
    elif c == 'type':   type_text(parts[1])
    elif c == 'key':    key(parts[1])
    elif c == 'scroll': scroll(int(parts[1]), int(parts[2]), int(parts[3]))
    elif c == 'sleep':  time.sleep(float(parts[1]))
    else: raise SystemExit(f'unknown batch action: {c}')

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'shot':
        args = sys.argv[2:]
        out = args[0] if args and not args[0].startswith('--') else '/tmp/itd.jpg'
        scale = 1.0 if '--full' in args else 0.5
        if '--scale' in args: scale = float(args[args.index('--scale')+1])
        crop = None
        if '--crop' in args:
            crop = tuple(int(v) for v in args[args.index('--crop')+1].split(','))
        shot(out, scale, crop)
        sys.exit(0)
    elif cmd == 'batch':
        # one call, many actions, ONE screenshot afterwards — the token saver
        focus()
        for step in sys.argv[2].split(';'):
            step = step.strip()
            if step: run_action(shlex.split(step))
    elif cmd == 'click':
        focus(); click(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == 'dblclick':
        focus(); click(int(sys.argv[2]), int(sys.argv[3]), n=2)
    elif cmd == 'move':
        x,y = to_global(int(sys.argv[2]), int(sys.argv[3])); post_mouse(Quartz.kCGEventMouseMoved, x, y)
    elif cmd == 'type':
        focus(); type_text(sys.argv[2])
    elif cmd == 'paste':
        focus(); paste(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    elif cmd == 'key':
        focus(); key(sys.argv[2])
    elif cmd == 'scroll':
        focus(); scroll(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    print('ok')
