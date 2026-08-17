#!/usr/bin/env python3
"""Read the ITD utility's screen as TEXT via the macOS Accessibility API.

The utility is a Wails/WKWebView app: no DOM, no debug port — so screenshots
used to be the only feedback, and they dominate token cost. But the web view
DOES publish an accessibility tree, which is plain text and ~50x cheaper.

  axdump.py            -> visible text of the frontmost utility window
  axdump.py --fields   -> only interactive elements (fields/buttons/checkboxes)
                          with their values and window-fraction coords
  axdump.py --grep RE  -> only lines matching a regex
"""
import re, subprocess, sys
from ApplicationServices import (AXUIElementCreateApplication,
                                 AXUIElementCopyAttributeValue,
                                 AXValueGetValue, kAXValueCGPointType,
                                 kAXValueCGSizeType)
import Quartz

APP = 'ITDe-Filing-2026'
INTERACTIVE = {'AXTextField', 'AXTextArea', 'AXButton', 'AXCheckBox',
               'AXRadioButton', 'AXPopUpButton', 'AXComboBox', 'AXLink',
               'AXMenuButton', 'AXIncrementor'}


def unwrap(v, kind):
    if v is None:
        return None
    ok, out = AXValueGetValue(v, kind, None)
    return out if ok else None


def attr(el, name):
    err, val = AXUIElementCopyAttributeValue(el, name, None)
    return val if err == 0 else None


def app_element():
    pid = int(subprocess.run(['pgrep', '-n', APP],
                             capture_output=True, text=True).stdout.strip())
    return AXUIElementCreateApplication(pid)


def window_frame():
    from Quartz import (CGWindowListCopyWindowInfo,
                        kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    best = None
    for w in CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly,
                                        kCGNullWindowID):
        if APP.lower() in str(w.get('kCGWindowOwnerName', '')).lower():
            b = w.get('kCGWindowBounds')
            if b and b['Height'] > 200:
                if best is None or b['Width'] * b['Height'] > best[2] * best[3]:
                    best = (b['X'], b['Y'], b['Width'], b['Height'])
    return best


def walk(el, out, depth=0, limit=12000):
    if len(out) >= limit or depth > 45:
        return
    role = attr(el, 'AXRole') or ''
    title = attr(el, 'AXTitle')
    value = attr(el, 'AXValue')
    desc = attr(el, 'AXDescription')
    pos = attr(el, 'AXPosition')
    size = attr(el, 'AXSize')
    text = ' '.join(str(x) for x in (title, desc) if x)
    vtext = '' if value is None else str(value)
    if role in INTERACTIVE or text.strip() or vtext.strip():
        out.append((role, text.strip(), vtext.strip(), pos, size))
    kids = attr(el, 'AXChildren') or []
    for k in kids:
        walk(k, out, depth + 1, limit)


def main():
    fields_only = '--fields' in sys.argv
    pat = None
    if '--grep' in sys.argv:
        pat = re.compile(sys.argv[sys.argv.index('--grep') + 1], re.I)

    el = app_element()
    wins = attr(el, 'AXWindows') or []
    if not wins:
        print('no windows'); return
    frame = window_frame()
    out = []
    walk(wins[0], out)

    seen = set()
    for role, text, val, pos, size in out:
        if fields_only and role not in INTERACTIVE:
            continue
        line = f'{text} = {val}'.strip(' =') if (text or val) else ''
        if not line or line in seen:
            continue
        seen.add(line)
        coord = ''
        if role in INTERACTIVE and pos and size and frame:
            try:
                p = unwrap(pos, kAXValueCGPointType)
                sz = unwrap(size, kAXValueCGSizeType)
                if p is None or sz is None:
                    raise ValueError
                cx = p.x + sz.width / 2
                cy = p.y + sz.height / 2
                fx = (cx - frame[0]) / frame[2]
                fy = (cy - frame[1]) / frame[3]
                if -0.05 <= fx <= 1.05 and -0.05 <= fy <= 1.05:
                    coord = f'  @{fx:.3f},{fy:.3f}'
            except Exception:
                pass
        s = f'[{role[2:]}] {line}{coord}' if role in INTERACTIVE else line
        if pat and not pat.search(s):
            continue
        print(s)


if __name__ == '__main__':
    main()
