import json
from datetime import datetime, timezone


def build_payload(items, bucket_name, custom_domain, include_original):
    entries = []
    for item in items:
        meta = item.metadata or {}
        entry = {
            "key": meta.get("key", item.src),
            "size": item.size,
            "expires_at": meta.get("expires_at"),
            "url": meta.get("url", item.dst)
        }
        if include_original:
            entry["original_url"] = meta.get("original_url", item.dst)
        entries.append(entry)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bucket": bucket_name,
        "custom_domain": custom_domain or None,
        "count": len(entries),
        "items": entries
    }


def _format_size(size_bytes):
    size = float(size_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def write_txt(payload, path):
    lines = []
    lines.append("S3View Share Report")
    lines.append(f"Generated: {payload['generated_at']}")
    lines.append(f"Bucket: {payload['bucket']}")
    if payload["custom_domain"]:
        lines.append(f"Custom Domain: {payload['custom_domain']}")
    lines.append(f"Total Links: {payload['count']}")
    lines.append("=" * 60)
    lines.append("")

    for index, entry in enumerate(payload["items"], start=1):
        lines.append(f"[{index}] {entry['key']}")
        lines.append(f"    Size:    {_format_size(entry['size'])}")
        lines.append(f"    Expires: {entry['expires_at']}")
        lines.append(f"    Link:    {entry['url']}")
        if "original_url" in entry:
            lines.append(f"    Original: {entry['original_url']}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def write_json(payload, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


_CSS = ":root{--bg:#050505;--card:#101012;--text:#d8d8d8;--accent:#22d3ee;--muted:#6b7280;--border:#1f1f22;--danger:#f87171}*{box-sizing:border-box}body{font-family:monospace;background:var(--bg);color:var(--text);margin:0;padding:30px;max-width:960px;margin-left:auto;margin-right:auto}h1{font-size:20px;color:#fff;margin:0 0 4px 0}.meta{color:var(--muted);font-size:12px;margin-bottom:24px}.grid{display:flex;flex-direction:column;gap:12px}.card{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:6px;padding:16px 18px}.key{font-size:14px;color:#fff;word-break:break-all;margin-bottom:8px}.row{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:4px}.link-row{display:flex;gap:8px;margin-top:10px}.link-row input{flex:1;background:#000;border:1px solid var(--border);color:var(--accent);font-family:monospace;font-size:11px;padding:8px;border-radius:4px}.link-row button{background:var(--accent);color:#000;border:none;border-radius:4px;padding:8px 14px;font-family:monospace;font-weight:700;cursor:pointer;font-size:11px}.link-row button:hover{opacity:.85}.expired{border-left-color:var(--danger)}.countdown{font-size:11px;color:var(--accent)}.expired .countdown{color:var(--danger)}"

_JS = """
const DATA = __PAYLOAD__;
const grid = document.getElementById('grid');
function fmtRemaining(iso){
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return 'expired';
  const h = Math.floor(diff/3600000), m = Math.floor((diff%3600000)/60000);
  return h > 0 ? (h + 'h ' + m + 'm left') : (m + 'm left');
}
function render(){
  grid.innerHTML = '';
  DATA.items.forEach(entry => {
    const remaining = fmtRemaining(entry.expires_at);
    const card = document.createElement('div');
    card.className = 'card' + (remaining === 'expired' ? ' expired' : '');
    card.innerHTML = `
      <div class="key">${entry.key}</div>
      <div class="row"><span>Size: ${entry.size} bytes</span><span class="countdown">${remaining}</span></div>
      <div class="link-row">
        <input type="text" readonly value="${entry.url}">
        <button data-url="${entry.url}">COPY</button>
      </div>
    `;
    grid.appendChild(card);
  });
  grid.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(btn.getAttribute('data-url'));
      btn.textContent = 'COPIED';
      setTimeout(() => btn.textContent = 'COPY', 1200);
    });
  });
}
render();
setInterval(render, 30000);
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>S3View Share Links</title>
<style>{css}</style>
</head>
<body>
<h1>Share Links</h1>
<div class="meta">Bucket: {bucket} &middot; Generated: {generated_at} &middot; {count} link(s){domain_line}</div>
<div class="grid" id="grid"></div>
<script type="application/json" id="share-data">{payload_json}</script>
<script>{js}</script>
</body>
</html>"""


def write_html(payload, path):
    domain_line = f" &middot; Custom Domain: {payload['custom_domain']}" if payload["custom_domain"] else ""
    payload_json = json.dumps(payload)
    js = _JS.replace("__PAYLOAD__", payload_json)
    html = _HTML_TEMPLATE.format(
        css=_CSS,
        bucket=payload["bucket"],
        generated_at=payload["generated_at"],
        count=payload["count"],
        domain_line=domain_line,
        payload_json=payload_json,
        js=js
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)