#!/bin/bash
# Poll MF Central My Downloads until the CG statement stops being In Progress.
check() {
osascript << 'EOF' 2>/dev/null
tell application "Google Chrome"
  set out to "notab"
  repeat with w in windows
    repeat with t in tabs of w
      if URL of t contains "mfcentral" then
        execute t javascript "(function(){var e=[...document.querySelectorAll('a,li,span,div')].find(function(x){return x.textContent.trim()==='My Downloads'});if(e){e.click()}return 'ok'})()"
        delay 3
        set out to execute t javascript "(function(){var t=document.body.innerText;if(t.indexOf('In Progress')>-1)return 'INPROGRESS';if(t.indexOf('No Downloads')>-1)return 'EMPTY';var i=t.indexOf('S.NO');return 'READY:'+(i>-1?t.slice(i,i+220).replace(/\\n/g,'|'):t.slice(0,120).replace(/\\n/g,'|'))})()"
      end if
    end repeat
  end repeat
  return out
end tell
EOF
}

for i in $(seq 1 100); do
  s=$(check)
  echo "poll $i: $s"
  case "$s" in
    READY:*) echo "STATEMENT READY"; exit 0 ;;
    INPROGRESS|notab|EMPTY|"") : ;;
    *) echo "UNEXPECTED: $s"; exit 0 ;;
  esac
  until [ $((SECONDS % 45)) -eq 0 ]; do sleep 1; done
done
echo "TIMED OUT after ~45 min"
