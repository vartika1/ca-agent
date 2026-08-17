#!/usr/bin/env python3
"""Act on the ITD utility through the Accessibility API — by LABEL, not pixels.

  axact.py press  'regex'          -> AXPress the first matching control
  axact.py set    'regex' VALUE    -> set a text field's value directly
  axact.py list   'regex'          -> show matching controls (role + value)

No screenshots, no coordinates, no scrolling: the control is found in the
accessibility tree wherever it is on the page. macOS only (the Windows
equivalent is UI Automation via pywinauto — same tree, same idea).
"""
import re, subprocess, sys
from ApplicationServices import (AXUIElementCreateApplication,
                                 AXUIElementCopyAttributeValue,
                                 AXUIElementPerformAction,
                                 AXUIElementSetAttributeValue,
                                 AXValueGetValue, kAXValueCGPointType,
                                 kAXValueCGSizeType)
import Quartz, time

APP = 'ITDe-Filing-2026'


def attr(el, name):
    err, val = AXUIElementCopyAttributeValue(el, name, None)
    return val if err == 0 else None


def root():
    pid = int(subprocess.run(['pgrep', '-n', APP],
                             capture_output=True, text=True).stdout.strip())
    wins = attr(AXUIElementCreateApplication(pid), 'AXWindows') or []
    return wins[0] if wins else None


def walk(el, out, depth=0):
    if depth > 45 or len(out) > 15000:
        return
    out.append(el)
    for k in (attr(el, 'AXChildren') or []):
        walk(k, out, depth + 1)


def label(el):
    return ' '.join(str(x) for x in
                    (attr(el, 'AXTitle'), attr(el, 'AXDescription'),
                     attr(el, 'AXValue')) if x)


def find(pat, roles=None):
    rx = re.compile(pat, re.I)
    els = []
    walk(root(), els)
    hits = []
    for el in els:
        r = attr(el, 'AXRole') or ''
        if roles and r not in roles:
            continue
        if rx.search(label(el)):
            hits.append((r, label(el)[:130], el))
    return hits


def mouse_click(el):
    """Real mouse click at the element's own centre (for non-pressable nodes
    like dropdown options rendered as static text)."""
    okp, p = AXValueGetValue(attr(el, 'AXPosition'), kAXValueCGPointType, None)
    oks, sz = AXValueGetValue(attr(el, 'AXSize'), kAXValueCGSizeType, None)
    if not (okp and oks):
        print('no geometry'); return False
    x, y = p.x + sz.width / 2, p.y + sz.height / 2
    ev = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved,
                                        (x, y), Quartz.kCGMouseButtonLeft)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
    time.sleep(0.15)
    for k in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
        ev = Quartz.CGEventCreateMouseEvent(None, k, (x, y),
                                            Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)
        time.sleep(0.06)
    print(f'clicked at {x:.0f},{y:.0f}')
    return True


def main():
    cmd, pat = sys.argv[1], sys.argv[2]
    if cmd == 'list':
        for r, l, _ in find(pat):
            print(f'[{r[2:]}] {l}')
    elif cmd in ('press', 'pressall', 'pressn'):
        hits = find(pat, roles={'AXButton', 'AXCheckBox', 'AXRadioButton',
                                'AXLink', 'AXPopUpButton', 'AXMenuButton'})
        if not hits:
            print('NO MATCH'); sys.exit(1)
        if cmd == 'pressall':
            for r, l, el in hits:
                AXUIElementPerformAction(el, 'AXPress')
                time.sleep(0.25)
            print(f'pressed {len(hits)} matches')
            return
        if cmd == 'pressn':
            n = int(sys.argv[3])
            if n >= len(hits):
                print(f'only {len(hits)} matches'); sys.exit(1)
            r, l, el = hits[n]
            print(f'pressing #{n} [{r[2:]}] {l[:70]}')
            AXUIElementPerformAction(el, 'AXPress')
            return
        r, l, el = hits[0]
        print(f'pressing [{r[2:]}] {l}')
        AXUIElementPerformAction(el, 'AXPress')
    elif cmd == 'click':
        hits = find(pat)
        if not hits:
            print('NO MATCH'); sys.exit(1)
        # prefer an exact-ish match: shortest label wins
        hits.sort(key=lambda h: len(h[1]))
        r, l, el = hits[0]
        print(f'clicking [{r[2:]}] {l}')
        mouse_click(el)
    elif cmd == 'set':
        hits = find(pat, roles={'AXTextField', 'AXTextArea', 'AXComboBox'})
        if not hits:
            print('NO MATCH'); sys.exit(1)
        r, l, el = hits[0]
        AXUIElementSetAttributeValue(el, 'AXValue', sys.argv[3])
        print(f'set [{r[2:]}] {l} -> {sys.argv[3]}')


if __name__ == '__main__':
    main()
