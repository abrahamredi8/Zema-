"""Bundle the owned UI for a Colab visual preview without public hosting.
API generation and real account sign-in are intentionally disconnected here.
"""
from pathlib import Path
import html
import re


def build_preview(root):
    public=Path(root)/'public'
    def inline(source):
        source=source.replace('<link rel="stylesheet" href="/workspace.css">','<style>'+ (public/'workspace.css').read_text()+'</style>')
        source=re.sub(r'<script src="/([a-z-]+\.js)" defer></script>',lambda m:'<script>'+ (public/m.group(1)).read_text()+'</script>',source)
        return source
    source=(public/'index.html').read_text().replace('<script type="module" src="/firebase-auth.js"></script>','<script src="/preview.js" defer></script>')
    dialogue=inline((public/'studio.html').read_text().replace('<body>', '<body class="embedded">'))
    source=re.sub(r'<iframe id="dialogueTool"[^>]*></iframe>',lambda m:'<iframe id="dialogueTool" title="Dialogue planning preview" data-src="about:blank" srcdoc="'+html.escape(dialogue,quote=True)+'"></iframe>',source)
    note='<body style="background:#0b1020;color:#aab8d2;font:18px system-ui;padding:20px"><h2>Video engine connection</h2><p>The real video studio is included in the app. This visual preview has no GPU endpoint or API credentials.</p></body>'
    source=re.sub(r'<iframe id="videoTool"[^>]*></iframe>',lambda m:'<iframe id="videoTool" title="Video connection preview" data-src="about:blank" srcdoc="'+html.escape(note,quote=True)+'"></iframe>',source)
    return inline(source)
