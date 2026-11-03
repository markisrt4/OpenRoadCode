# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Execute the permission page's async recovery and consent behavior."""
import re
import shutil
import subprocess
import pytest

from controllers.navigation.browser_position_source import _LOCATION_PAGE


@pytest.mark.skipif(shutil.which('node') is None, reason='JavaScript runtime unavailable')
def test_relay_reconnects_after_restart_but_stop_and_denial_cancel_retries():
    script = re.search(rb'<script>(.*?)</script>', _LOCATION_PAGE, re.S)[1].decode()
    harness = r'''
const assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs');
const elements={status:{},start:{disabled:false},stop:{disabled:true},close:{}}, timers=new Map(), fixes=[];
let timerId=0, online=false, posts=0, hides=0;
const context={document:{querySelector:s=>elements[s.slice(1)]},
 navigator:{geolocation:{getCurrentPosition:(ok,fail)=>fixes.push({ok,fail})}},
 window:{addEventListener:()=>{},location:{hash:'#window=8767'}}, AbortController, URLSearchParams,
 setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,delay});return timerId;},
 clearTimeout:id=>timers.delete(id),
 fetch:async url=>{if(url.endsWith('/hide')){hides++;return {ok:true};}
   posts++;if(!online)throw Error('server stopped');return {ok:true};}};
vm.runInNewContext(fs.readFileSync(0,'utf8'),context);
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const fix={coords:{latitude:42,longitude:-83,accuracy:20,altitude:0}};
(async()=>{
 elements.start.onclick(); fixes.at(-1).ok(fix); await tick();
 assert.equal(posts,1); assert.equal(elements.start.disabled,true);
 assert.match(elements.status.textContent,/reconnect/);
 const retry=[...timers.values()].find(t=>t.delay===2000);
 assert.ok(retry); online=true; retry.fn(); fixes.at(-1).ok(fix); await tick();
 assert.equal(posts,2); assert.match(elements.status.textContent,/Sharing live/);
 await elements.close.onclick(); assert.equal(hides,1); assert.equal(elements.start.disabled,true);
 const afterHide=[...timers.values()].find(t=>t.delay===5000);
 afterHide.fn(); fixes.at(-1).ok(fix); await tick(); assert.equal(posts,3);
 elements.stop.onclick(); const count=fixes.length; retry.fn();
 assert.equal(fixes.length,count); assert.equal(elements.start.disabled,false);
 elements.start.onclick(); fixes.at(-1).fail({code:1,message:'Permission denied'});
 assert.equal(elements.start.disabled,false); assert.match(elements.status.textContent,/denied/);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
    result = subprocess.run(['node', '-e', harness], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
