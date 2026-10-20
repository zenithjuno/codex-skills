#!/usr/bin/env python3
"""Shared macOS Word PDF export, always opening a private copy. No source save."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path


def apple_string(value):
    return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\r','\\r')+'"'


def export_pdf(src, dst, timeout=45):
    src,dst=Path(src).resolve(),Path(dst).resolve()
    result={'status':'ERROR','reason':'','source':str(src),'pdf':str(dst)}
    if not src.is_file() or src==dst or src.suffix.lower()!='.docx' or dst.suffix.lower()!='.pdf':
        return dict(result,reason='Expected distinct existing DOCX input and PDF output')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not 1<=timeout<=300:
        return dict(result,reason='timeout must be between 1 and 300 seconds')
    container=Path.home()/'Library/Containers/com.microsoft.Word/Data'
    if sys.platform!='darwin' or not Path('/usr/bin/osascript').exists() or not container.is_dir():
        return dict(result,status='SKIPPED',reason='Microsoft Word for macOS is unavailable')
    before=hashlib.sha256(src.read_bytes()).hexdigest();result['source_sha256_before']=before
    work=None;opened=False
    try:
        work=Path(tempfile.mkdtemp(prefix='codex-word-',dir=container))
        inp,out=work/'input.docx',work/'output.pdf';shutil.copyfile(src,inp)
        # AppleScript keeps a reference to only the document it opened. Never use
        # active document or quit Word; existing teacher documents remain open.
        script=f'''with timeout of {int(timeout)} seconds
set ownedDocument to missing value
tell application "Microsoft Word"
    try
        set ownedDocument to open file name {apple_string(inp)}
        save as ownedDocument file name {apple_string(out)} file format format PDF
        close ownedDocument saving no
    on error errText number errNumber
        if ownedDocument is not missing value then
            try
                close ownedDocument saving no
            end try
        end if
        error errText number errNumber
    end try
end tell
end timeout
'''
        opened=True
        proc=subprocess.run(['/usr/bin/osascript','-'],input=script,text=True,capture_output=True,timeout=timeout+5)
        if proc.returncode:
            reason=proc.stderr.strip() or 'Word export returned no diagnostic'
            result.update(status='BLOCKED',reason=reason)
        elif not out.is_file() or not out.read_bytes().startswith(b'%PDF-'):
            result.update(reason='Word returned without producing a valid PDF')
        else:
            dst.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='.word-pdf-',dir=dst.parent);os.close(fd)
            try:shutil.copyfile(out,tmp);os.replace(tmp,dst)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
            result.update(status='EXPORTED',reason='Exported a private copy; no source save')
    except (PermissionError,subprocess.TimeoutExpired) as exc:
        result.update(status='BLOCKED',reason=str(exc))
    except OSError as exc:
        result.update(status='ERROR',reason=str(exc))
    finally:
        # Even a timed-out Apple Event may have opened the copy. Attempt bounded
        # cleanup of that exact file, never a teacher document. Word rejects
        # `repeat with x in documents` (-1708) and reports HFS full names, so
        # iterate by index and compare POSIX paths; no match means closed. Retain the temp
        # folder if we cannot confirm closure so Word does not lose its backing file.
        closed=not opened
        if work and opened:
            cleanup=f'''with timeout of 4 seconds
set target to {apple_string(work/'input.docx')}
tell application "Microsoft Word"
repeat with i from (count of documents) to 1 by -1
set candidate to document i
if POSIX path of ((full name of candidate) as text) is target then close candidate saving no
end repeat
end tell
end timeout'''
            try:
                check=subprocess.run(['/usr/bin/osascript','-'],input=cleanup,text=True,capture_output=True,timeout=6)
                closed=check.returncode==0
            except (OSError,subprocess.TimeoutExpired):closed=False
        if work:
            if closed:shutil.rmtree(work,ignore_errors=True)
            else:result['cleanup_pending']=str(work)
        after=hashlib.sha256(src.read_bytes()).hexdigest()
        result.update(source_sha256_after=after,source_unchanged=before==after)
        if before!=after:result.update(status='ERROR',reason='Source changed during export; possible concurrent edit')
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input');ap.add_argument('output');ap.add_argument('--timeout',type=int,default=45);ap.add_argument('--json',action='store_true')
    a=ap.parse_args(argv);r=export_pdf(a.input,a.output,a.timeout)
    print(json.dumps(r,ensure_ascii=False) if a.json else f"{r['status']}: {r['reason']} — {r['pdf']}")
    return 0 if r['status']=='EXPORTED' else 2 if r['status'] in {'BLOCKED','SKIPPED'} else 1

if __name__=='__main__':raise SystemExit(main())
