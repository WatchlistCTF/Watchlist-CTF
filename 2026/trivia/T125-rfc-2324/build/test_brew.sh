#!/usr/bin/env bash
# Usage: ./test_brew.sh https://teapot.northernlights.gg   (no trailing slash)
# The critical check is the last one: that BREW survives your proxy/CDN from the public internet.
B="${1:?usage: ./test_brew.sh <base-url>}"
pass=0; fail=0
chk(){ d="$1";ec="$2";es="$3";shift 3
  c=$(curl -s -o /tmp/b -w "%{http_code}" "$@");b=$(cat /tmp/b);ok=1
  [ "$c" = "$ec" ]||ok=0; [ -n "$es" ]&&{ echo "$b"|grep -q "$es"||ok=0;}
  [ $ok = 1 ]&&{ echo "PASS [$c] $d";pass=$((pass+1));}||{ echo "FAIL [$c want $ec] $d";fail=$((fail+1));}; }
chk "GET greeting"        200 "RFC 2324"            "$B/"
chk "GET /coffee 418"     418 "teapot"             "$B/coffee"
chk "POST 418"            418 "teapot"             -X POST "$B/pot-0"
chk "BREW no type 415"    415 "message/coffeepot"  -X BREW -d start "$B/pot-0"
chk "BREW wrong body 400" 400 "start"              -X BREW -H "Content-Type: message/coffeepot" -d nope "$B/pot-0"
chk "BREW correct -> FLAG" 200 "the_machine_takes_it_black" -X BREW -H "Content-Type: message/coffeepot" -d start "$B/pot-0"
echo "--- $pass passed, $fail failed ---"
[ $fail = 0 ] && echo "BREW survives the proxy. T125 is live." || echo "Something blocks BREW or the service is down."
