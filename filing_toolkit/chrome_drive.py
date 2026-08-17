#!/usr/bin/env python
"""Drive Google Chrome via Quartz using WINDOW-FRACTION coords (retina-safe).
Usage:
  chrome_drive.py shot [out.png]        - capture main Chrome window
  chrome_drive.py click FX FY           - click at fraction (0..1) of window
  chrome_drive.py move FX FY
Fractions are of the window's logical W/H, so retina 2x doesn't matter.
"""
import sys, time, subprocess
import Quartz

def win():
    import os
    target=os.environ.get('CHROME_WIN')
    wins = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID)
    best=None
    for w in wins:
        if 'Chrome' in str(w.get('kCGWindowOwnerName','')) and w.get('kCGWindowLayer',1)==0:
            b=w['kCGWindowBounds']
            num=int(w['kCGWindowNumber'])
            if target and str(num)==target:
                return num,b['X'],b['Y'],b['Width'],b['Height']
            if b['Width']>800 and b['Height']>500:
                area=b['Width']*b['Height']
                if not best or area>best[0]:
                    best=(area,num,b['X'],b['Y'],b['Width'],b['Height'])
    if not best: raise SystemExit('Chrome window not found')
    return best[1],best[2],best[3],best[4],best[5]

def to_global(fx,fy):
    _,X,Y,W,H=win()
    return X+fx*W, Y+fy*H

def post(kind,x,y,clicks=1):
    ev=Quartz.CGEventCreateMouseEvent(None,kind,(x,y),Quartz.kCGMouseButtonLeft)
    Quartz.CGEventSetIntegerValueField(ev,Quartz.kCGMouseEventClickState,clicks)
    Quartz.CGEventPost(Quartz.kCGHIDEventTap,ev)

def click(fx,fy,n=1):
    subprocess.run(['osascript','-e','tell application "Google Chrome" to activate'],capture_output=True)
    time.sleep(0.3)
    x,y=to_global(fx,fy)
    post(Quartz.kCGEventMouseMoved,x,y); time.sleep(0.15)
    for i in range(n):
        post(Quartz.kCGEventLeftMouseDown,x,y,i+1); time.sleep(0.05)
        post(Quartz.kCGEventLeftMouseUp,x,y,i+1); time.sleep(0.08)

def shot(out):
    wid=win()[0]
    subprocess.run(['screencapture','-x','-o','-l',str(wid),out],check=True)
    print(out)

if __name__=='__main__':
    cmd=sys.argv[1]
    if cmd=='shot': shot(sys.argv[2] if len(sys.argv)>2 else '/tmp/chrome.png')
    elif cmd=='click': click(float(sys.argv[2]),float(sys.argv[3]))
    elif cmd=='dblclick': click(float(sys.argv[2]),float(sys.argv[3]),n=2)
    elif cmd=='move':
        x,y=to_global(float(sys.argv[2]),float(sys.argv[3])); post(Quartz.kCGEventMouseMoved,x,y)
    print('ok')
