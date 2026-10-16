# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import json
import shutil
import subprocess
import unittest
from frontends.common.destination_map_confirmation import HTML


@unittest.skipUnless(shutil.which("node"), "Node is needed for browser feedback checks")
class DestinationMapFeedbackTest(unittest.TestCase):
    def test_confirm_click_reports_success_and_network_failure(self):
        script = HTML.split("<script>", 1)[1].split("</script>", 1)[0].replace(
            "__DATA__", json.dumps(dict(label="Work", address="Example", lat=42.5, lon=-83, token="test"))
        )
        harness = r'''
const vm=require('vm'),assert=require('assert');
async function check(fail){
const elements={};const doc={querySelector:key=>elements[key]||(elements[key]={style:{},clientWidth:320,clientHeight:400,replaceChildren(){},append(){}}),createElement:()=>({style:{}})};
const context={document:doc,window:{},AbortController,setTimeout,clearTimeout,fetch:async()=>{if(fail)throw Error('offline');return{ok:true,json:async()=>({confirmed:true})}}};
vm.runInNewContext(SCRIPT,context);
const pending=context.finish(false);
assert.equal(elements['#status'].textContent,'Confirming location…');
await pending;
assert(elements['#status'].textContent.includes(fail?'could not reach':'Return to'));
if(!fail)assert.equal(elements['#use'].textContent,'Location confirmed ✓');
}
(async()=>{await check(false);await check(true)})().catch(e=>{console.error(e);process.exitCode=1});
'''.replace("SCRIPT", json.dumps(script))
        subprocess.run([shutil.which("node"), "-e", harness], check=True, capture_output=True, text=True)
