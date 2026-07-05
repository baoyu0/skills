#!/usr/bin/env python3
"""
obu_extract.py — Extract X Article video info via obu (call from terminal).
Called by cleanup command. Saves JSON result to output path.

Usage: python3 obu_extract.py <article_url> <output_json_path>
"""
import subprocess, json, sys, time, os, shlex, tempfile

OBU = "/d/npm-global/obu"
temp_dir = tempfile.gettempdir()

def run(cmd, timeout=30):
    """Run a shell command, return stdout."""
    # cmd is a list of args; obu is a shell script so use bash
    full_cmd = " ".join(f'"{a}"' if " " in a else a for a in cmd)
    r = subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c", full_cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr

def cdp(tab_id, js_expr):
    """Evaluate JS via obu CDP, return result value."""
    params = json.dumps({"expression": js_expr, "returnByValue": True})
    tmp = os.path.join(temp_dir, f"cdp_{os.getpid()}_{time.time_ns()}.json")
    cmd_str = f'\"{OBU}\" cdp --tab-id {tab_id} --method Runtime.evaluate --params {shlex.quote(params)} > \"{tmp}\" 2>&1'
    subprocess.run(["C:/Program Files/Git/bin/bash.exe", "-c", cmd_str],
                   capture_output=True, timeout=30)
    try:
        with open(tmp) as f:
            stdout = f.read()
        os.remove(tmp)
    except FileNotFoundError:
        return None
    # CDP output is multi-line JSON; accumulate until balanced braces
    buf = ""
    depth = 0
    for ch in stdout:
        buf += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and buf.startswith("{"):
                try:
                    d = json.loads(buf)
                    v = d.get("result", {}).get("result", {}).get("value")
                    if v is not None:
                        return v
                except json.JSONDecodeError:
                    pass
                buf = ""
    return None

def click(tab_id, x, y):
    """Click at coordinates via CDP Input."""
    for _ in range(3):
        for evt in ["mousePressed", "mouseReleased"]:
            params = json.dumps({"type": evt, "x": x, "y": y,
                                 "button": "left", "clickCount": 1})
            run([OBU, "cdp", "--tab-id", str(tab_id),
                 "--method", "Input.dispatchMouseEvent", "--params", params])
            time.sleep(0.1)
        time.sleep(0.3)

def extract(url, output_path):
    result = {"status": "error", "note": ""}
    tab_id = None

    try:
        # Step 1: Open tab
        stdout, stderr = run([OBU, "open-tab", "--url", url])
        # Parse multi-line JSON for open-tab response
        buf = ""; depth = 0
        for ch in stdout:
            buf += ch
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and buf.startswith("{"):
                    try:
                        d = json.loads(buf)
                        tab_id = d.get("tab", {}).get("id")
                        if tab_id: break
                    except: pass
                    buf = ""
        if not tab_id:
            result["note"] = "failed to open tab"
            json.dump(result, open(output_path, "w"))
            return

        time.sleep(8)

        # Step 2: Count + posters
        info_raw = cdp(tab_id,
            'JSON.stringify({count:document.querySelectorAll("video").length,'
            'posters:Array.from(document.querySelectorAll("video")).map(function(v){return v.poster||""})})')
        if not info_raw:
            result["note"] = "no video data"
            json.dump(result, open(output_path, "w"))
            return

        info = json.loads(info_raw)
        count = info.get("count", 0)
        posters = info.get("posters", [])

        if count == 0:
            result = {"status": "done", "posters": [], "cdn_urls": [],
                      "note": "no videos", "videos": []}
            json.dump(result, open(output_path, "w"))
            obu_cleanup(tab_id)
            return

        # Step 3: Find play button and click
        btn_js = (
            '(function(){'
            'var v=document.querySelector("video");'
            'var el=v;'
            'for(var i=0;i<4;i++)el=el.parentElement;'
            'var btns=el.querySelectorAll("button");'
            'for(var i=0;i<btns.length;i++){'
            'var b=btns[i];var r=b.getBoundingClientRect();'
            'if(r.width>0&&r.height>0)return Math.round(r.left+r.width/2)+","+Math.round(r.top+r.height/2)}'
            'return"0,0"})()')
        rc_raw = cdp(tab_id, btn_js) or "0,0"
        parts = rc_raw.split(",")
        if len(parts) == 2 and parts[0] != "0":
            click(tab_id, int(parts[0]), int(parts[1]))
            time.sleep(15)

        # Step 4: CDN URLs (best effort)
        cdn_raw = cdp(tab_id,
            'JSON.stringify(performance.getEntriesByType("resource")'
            '.filter(function(e){return e.name.includes("twimg")})'
            '.map(function(e){return{url:e.name.slice(0,200)}}))') or "[]"
        cdn_urls = json.loads(cdn_raw)
        cdn_list = [c["url"] for c in cdn_urls]

        result = {
            "status": "done",
            "posters": posters,
            "cdn_urls": cdn_list,
            "videos": [{"idx": i, "poster": p} for i, p in enumerate(posters)],
            "note": "cdn_found" if cdn_list else "cdn_empty (MSE streaming)"
        }
        json.dump(result, open(output_path, "w"))

    except Exception as e:
        result["note"] = str(e)
        json.dump(result, open(output_path, "w"))
    finally:
        # Always clean up session tabs regardless of when/why we exit
        run([OBU, "finalize-tabs", "--keep", "[]"])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <url> <output.json>")
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2])
