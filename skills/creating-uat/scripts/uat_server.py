#!/usr/bin/env python3
"""Local helper for filling in a UAT.

    python uat_server.py path/to/UAT-myapp-2026-08-23.md

Regenerates the HTML form, serves it at http://localhost:8777, and:
  * Save        -> writes .uat-progress-<slug>.json so nothing is ever lost
  * screenshots -> saved into assets/<slug>/ and linked from the markdown
  * Submit      -> validates, then writes the answers back into the markdown
                   and drops a machine-readable <name>.results.json

Standard library only. Binds to 127.0.0.1 (this computer only). Stop it with Ctrl+C.
"""

import argparse
import base64
import binascii
import datetime
import json
import mimetypes
import os
import posixpath
import re
import socket
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_uat_html as gen  # noqa: E402

MAX_UPLOAD = 8 * 1024 * 1024
MAX_BODY = 24 * 1024 * 1024
EXT_BY_MIME = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
               "image/webp": ".webp", "image/avif": ".avif"}
STATUS_MD = {"pass": ("x", "PASS"), "fail": ("!", "FAIL"), "notdone": ("~", "NOT DONE")}
SEV_LABEL = {"cosmetic": "Cosmetic", "annoying": "Annoying", "blocker": "Blocks me"}


class Ctx(object):
    def __init__(self, md_path):
        self.md_path = os.path.abspath(md_path)
        self.dir = os.path.dirname(self.md_path)
        self.slug = os.path.splitext(os.path.basename(self.md_path))[0]
        self.html_path = os.path.join(self.dir, self.slug + ".html")
        self.progress_path = os.path.join(self.dir, ".uat-progress-%s.json" % self.slug)
        self.results_path = os.path.join(self.dir, self.slug + ".results.json")
        self.assets_dir = os.path.join(self.dir, "assets", self.slug)
        self.lock = threading.Lock()

    def load_md(self):
        with open(self.md_path, "r", encoding="utf-8") as fh:
            return fh.read().replace("\r\n", "\n").split("\n")

    def index(self):
        """{test_id: {title, section}} plus parsed spans, from the current markdown."""
        lines = self.load_md()
        meta, sections, spans = gen.parse(lines, self.md_path)
        info = {}
        for s in sections:
            for t in s["tests"]:
                info[t["id"]] = {"title": t["title"], "section": s["id"]}
        return lines, meta, sections, spans, info


# ------------------------------------------------------------------ validation

def validate(state, info, partial):
    problems = []
    if not (state.get("tester") or "").strip():
        problems.append({"id": None, "msg": "No tester name was filled in."})
    answers = state.get("answers") or {}
    for tid in info:
        a = answers.get(tid) or {}
        status = (a.get("status") or "").strip()
        notes = (a.get("notes") or "").strip()
        concern = (a.get("concern") or "").strip()
        if not status:
            if not partial:
                problems.append({"id": tid, "msg": "Test %s has no answer yet." % tid})
            continue
        if status not in STATUS_MD:
            problems.append({"id": tid, "msg": "Test %s has an unknown status %r." % (tid, status)})
            continue
        if status in ("fail", "notdone") and len(notes) < 10:
            problems.append({"id": tid, "msg": "Test %s is marked %s but has no explanation."
                             % (tid, STATUS_MD[status][1])})
        if concern and not (a.get("severity") or "").strip():
            problems.append({"id": tid, "msg": "Test %s has a look-and-feel comment with no severity." % tid})
    for f in state.get("findings") or []:
        fid = f.get("id", "?")
        if not (f.get("title") or "").strip():
            problems.append({"id": fid, "msg": "Finding %s has no title." % fid})
        if not (f.get("description") or "").strip():
            problems.append({"id": fid, "msg": "Finding %s has no description." % fid})
        if not (f.get("severity") or "").strip():
            problems.append({"id": fid, "msg": "Finding %s has no severity." % fid})
    return problems


def counts_of(state, info):
    c = {"pass": 0, "fail": 0, "notdone": 0, "unanswered": 0, "concerns": 0,
         "findings": len(state.get("findings") or [])}
    answers = state.get("answers") or {}
    for tid in info:
        a = answers.get(tid) or {}
        st = a.get("status") or ""
        c[st if st in STATUS_MD else "unanswered"] += 1
        if (a.get("concern") or "").strip():
            c["concerns"] += 1
    return c


# ------------------------------------------------------------- markdown writing

def shot_lines(owner, shots):
    out = []
    for i, s in enumerate(shots or []):
        path = s.get("path") if isinstance(s, dict) else s
        if not path or path.startswith("data:"):
            continue
        out.append("  - ![%s screenshot %d](%s)" % (owner, i + 1, path))
    return out


def answer_md(tid, a):
    a = a or {}
    status = a.get("status") or ""
    notes = (a.get("notes") or "").strip()
    concern = (a.get("concern") or "").strip()
    sev = SEV_LABEL.get((a.get("severity") or "").strip(), "")
    if status in STATUS_MD:
        box, label = STATUS_MD[status]
        head = "- [%s] **Status:** %s" % (box, label)
    else:
        head = "- [ ] **Status:** _not answered_"
    lines = [head]
    lines.append("- **Notes:** " + (notes.replace("\n", "\n  ") if notes else "_none_"))
    if concern:
        lines.append("- **Look & feel concern:** (%s) %s" % (sev or "unrated", concern.replace("\n", "\n  ")))
    else:
        lines.append("- **Look & feel concern:** _none_")
    shots = shot_lines(tid, a.get("screenshots"))
    lines.append("- **Screenshots:**" + ("" if shots else " _none_"))
    lines.extend(shots)
    return lines


def summary_md(state, info, counts, partial, when):
    tester = (state.get("tester") or "").strip() or "unnamed tester"
    answers = state.get("answers") or {}
    failed = sorted([t for t in info if (answers.get(t) or {}).get("status") == "fail"], key=natural)
    notdone = sorted([t for t in info if (answers.get(t) or {}).get("status") == "notdone"], key=natural)
    concerned = sorted([t for t in info if ((answers.get(t) or {}).get("concern") or "").strip()], key=natural)
    unanswered = sorted([t for t in info if not (answers.get(t) or {}).get("status")], key=natural)
    total = len(info)
    lines = [
        "> **Run status:** %s — submitted %s by %s" % ("PARTIAL (unfinished)" if partial else "COMPLETE", when, tester),
        "> **Result:** %d of %d passed · %d failed · %d not done · %d look-and-feel concerns · %d other findings"
        % (counts["pass"], total, counts["fail"], counts["notdone"], counts["concerns"], counts["findings"]),
        ">",
        "> | Status | Count |",
        "> |---|---|",
        "> | Pass | %d |" % counts["pass"],
        "> | Fail | %d |" % counts["fail"],
        "> | Not done | %d |" % counts["notdone"],
        "> | Unanswered | %d |" % counts["unanswered"],
        ">",
    ]
    lines.append("> **Failed tests:** " + (", ".join(failed) if failed else "none"))
    if notdone:
        lines.append("> **Not done:** " + ", ".join(notdone))
    lines.append("> **Tests with look-and-feel concerns:** " + (", ".join(concerned) if concerned else "none"))
    if unanswered:
        lines.append("> **Never answered:** " + ", ".join(unanswered))
    return lines


def findings_md(state):
    fs = state.get("findings") or []
    head = ["## Anything else the tester noticed", ""]
    if not fs:
        return head + ["_No tester-reported findings._"]
    out = list(head)
    for f in fs:
        fid = f.get("id", "F?")
        out.append("### %s — %s" % (fid, (f.get("title") or "").strip() or "(no title)"))
        sec = (f.get("section") or "").strip()
        out.append("- **Reported from:** " + ("Section %s" % sec if sec else "the end of the checklist"))
        out.append("- **Severity:** " + SEV_LABEL.get((f.get("severity") or "").strip(), "unrated"))
        out.append("- **What happened:** " + (f.get("description") or "").strip().replace("\n", "\n  "))
        shots = shot_lines(fid, f.get("screenshots"))
        out.append("- **Screenshots:**" + ("" if shots else " _none_"))
        out.extend(shots)
        out.append("")
    return out[:-1]


def natural(s):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", str(s))]


def write_markdown(ctx, state, partial):
    with ctx.lock:
        lines, meta, sections, spans, info = ctx.index()
        counts = counts_of(state, info)
        when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        answers = state.get("answers") or {}

        edits = []  # (start, end_inclusive, replacement_lines) — markers kept, body replaced
        for tid, span in spans["answers"].items():
            edits.append((span[0] + 1, span[1] - 1, answer_md(tid, answers.get(tid))))
        if spans["summary"]:
            edits.append((spans["summary"][0] + 1, spans["summary"][1] - 1,
                          summary_md(state, info, counts, partial, when)))
        if spans["findings"]:
            edits.append((spans["findings"][0] + 1, spans["findings"][1] - 1, findings_md(state)))

        for start, end, repl in sorted(edits, key=lambda e: -e[0]):
            lines[start:end + 1] = repl

        # refresh the meta block's tester/date lines if present
        if spans["meta"]:
            ms, me = spans["meta"]
            block = lines[ms:me + 1]
            block = [l for l in block if not l.strip().startswith(("tester:", "last_run:"))]
            block = block[:-1] + ["tester: " + (state.get("tester") or "").strip(),
                                  "last_run: " + when] + block[-1:]
            lines[ms:me + 1] = block

        with open(ctx.md_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))

        results = {
            "uat": os.path.basename(ctx.md_path),
            "tester": (state.get("tester") or "").strip(),
            "submitted": datetime.datetime.now().isoformat(timespec="seconds"),
            "partial": bool(partial),
            "counts": counts,
            "answers": {},
            "findings": state.get("findings") or [],
        }
        for tid, meta_t in info.items():
            a = answers.get(tid) or {}
            results["answers"][tid] = {
                "status": a.get("status") or "unanswered",
                "title": meta_t["title"],
                "section": meta_t["section"],
                "notes": (a.get("notes") or "").strip(),
                "concern": (a.get("concern") or "").strip(),
                "severity": (a.get("severity") or "").strip(),
                "screenshots": [s.get("path") for s in (a.get("screenshots") or [])
                                if isinstance(s, dict) and s.get("path", "").startswith("assets/")],
            }
        with open(ctx.results_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)

        return counts, results


# ---------------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    ctx = None
    server_version = "UATHelper/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # --- helpers

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            raise ValueError("request body missing or too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def safe_path(self, url_path):
        rel = posixpath.normpath(url_path.lstrip("/"))
        if rel in ("", "."):
            return self.ctx.html_path
        if rel.startswith("..") or os.path.isabs(rel):
            return None
        full = os.path.abspath(os.path.join(self.ctx.dir, *rel.split("/")))
        if os.path.commonpath([full, self.ctx.dir]) != self.ctx.dir:
            return None
        return full

    # --- routes

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            state = {}
            if os.path.exists(self.ctx.progress_path):
                try:
                    with open(self.ctx.progress_path, "r", encoding="utf-8") as fh:
                        state = json.load(fh)
                except Exception:
                    state = {}
            return self.send_json({"state": state})
        full = self.safe_path(path)
        if not full or not os.path.isfile(full):
            return self.send_json({"error": "not found"}, 404)
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as fh:
            data = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            payload = self.read_json()
        except Exception as exc:
            return self.send_json({"error": "bad request: %s" % exc}, 400)

        if path == "/api/save":
            state = payload.get("state") or {}
            state["updatedAt"] = int(datetime.datetime.now().timestamp() * 1000)
            with open(self.ctx.progress_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(state, fh, indent=2, ensure_ascii=False)
            print("  saved progress (%d answers)" % len(state.get("answers") or {}))
            return self.send_json({"ok": True})

        if path == "/api/upload":
            return self.handle_upload(payload)

        if path == "/api/submit":
            return self.handle_submit(payload)

        return self.send_json({"error": "unknown endpoint"}, 404)

    def handle_upload(self, payload):
        owner = str(payload.get("owner") or "").strip()
        if not owner or not gen.ID_RE.match(owner):
            return self.send_json({"error": "bad owner id"}, 400)
        data_url = payload.get("dataUrl") or ""
        m = re.match(r"^data:([\w/+.-]+);base64,(.*)$", data_url, re.S)
        if not m:
            return self.send_json({"error": "that file was not an image"}, 400)
        mime, b64 = m.group(1), m.group(2)
        if mime not in EXT_BY_MIME:
            return self.send_json({"error": "unsupported image type %s" % mime}, 400)
        try:
            raw = base64.b64decode(b64, validate=True)
        except (binascii.Error, ValueError):
            return self.send_json({"error": "the image could not be decoded"}, 400)
        if len(raw) > MAX_UPLOAD:
            return self.send_json({"error": "that image is larger than 8 MB"}, 400)
        os.makedirs(self.ctx.assets_dir, exist_ok=True)
        ext = EXT_BY_MIME[mime]
        n = 1
        while os.path.exists(os.path.join(self.ctx.assets_dir, "%s-%d%s" % (owner, n, ext))):
            n += 1
        name = "%s-%d%s" % (owner, n, ext)
        with open(os.path.join(self.ctx.assets_dir, name), "wb") as fh:
            fh.write(raw)
        rel = "assets/%s/%s" % (self.ctx.slug, name)
        print("  saved screenshot %s (%.0f KB)" % (rel, len(raw) / 1024.0))
        return self.send_json({"ok": True, "path": rel})

    def handle_submit(self, payload):
        state = payload.get("state") or {}
        partial = bool(payload.get("partial"))
        try:
            _, _, _, _, info = self.ctx.index()
        except gen.UatError as exc:
            return self.send_json({"error": "the checklist file has a problem: %s" % exc}, 500)
        problems = validate(state, info, partial)
        if problems:
            return self.send_json({"ok": False, "error": "Some answers are missing.", "problems": problems}, 200)

        state["updatedAt"] = int(datetime.datetime.now().timestamp() * 1000)
        with open(self.ctx.progress_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)

        try:
            counts, _ = write_markdown(self.ctx, state, partial)
        except Exception as exc:  # noqa: BLE001 - report anything back to the browser
            return self.send_json({"error": "could not write the checklist: %s" % exc}, 500)

        try:
            gen.generate(self.ctx.md_path, self.ctx.html_path, quiet=True)
        except Exception:
            pass

        summary = ("%d passed, %d failed, %d not done, %d look-and-feel concerns, %d other findings."
                   % (counts["pass"], counts["fail"], counts["notdone"], counts["concerns"], counts["findings"]))
        if partial:
            summary += " %d test(s) were left unanswered — the report is marked as unfinished." % counts["unanswered"]
        print("\n  SUBMITTED — %s" % summary)
        print("  wrote %s" % self.ctx.md_path)
        print("  wrote %s\n" % self.ctx.results_path)
        return self.send_json({
            "ok": True, "partial": partial, "summary": summary,
            "mdPath": self.ctx.md_path,
            "mdRel": os.path.basename(self.ctx.md_path),
            "results": self.ctx.results_path,
        })


def pick_port(preferred):
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("Could not find a free port between %d and %d." % (preferred, preferred + 19))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serve a UAT checklist form and write the answers back into the markdown.")
    ap.add_argument("markdown", help="path to the UAT .md file")
    ap.add_argument("-p", "--port", type=int, default=8777)
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = ap.parse_args(argv)

    if not os.path.isfile(args.markdown):
        print("No such file: %s" % args.markdown, file=sys.stderr)
        return 2
    ctx = Ctx(args.markdown)
    try:
        gen.generate(ctx.md_path, ctx.html_path, quiet=True)
    except gen.UatError as exc:
        print("UAT file problem: %s" % exc, file=sys.stderr)
        return 2

    port = pick_port(args.port)
    Handler.ctx = ctx
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = "http://localhost:%d/" % port

    print("")
    print("  UAT helper is running.")
    print("  Checklist : %s" % ctx.md_path)
    print("  Open this in your web browser:  %s" % url)
    print("  Leave this window open while you work. Press Ctrl+C here when you are finished.")
    print("")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. Your answers are in %s" % ctx.progress_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
