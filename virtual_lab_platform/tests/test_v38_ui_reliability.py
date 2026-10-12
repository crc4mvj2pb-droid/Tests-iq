from pathlib import Path
from collections import Counter
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
    def handle_starttag(self, tag, attrs):
        value = dict(attrs).get("id")
        if value:
            self.ids.append(value)

def test_visible_api_connection_status_and_offline_guidance_exist():
    assert 'id="apiConnectionStatus"' in HTML
    assert 'id="apiStatusBanner"' in HTML
    assert "python app.py" in HTML
    assert "fetch('/api/health'" in HTML

def test_workbench_can_explicitly_restore_saved_workspace():
    assert 'id="wbRestore"' in HTML
    assert "$('wbRestore').onclick=()=>restoreWorkspace(true)" in HTML
    assert "function restoreWorkspace(askFirst=true)" in HTML
    assert "Array.isArray(saved.bench)" in HTML

def test_storage_access_is_guarded_against_browser_security_errors():
    assert "const safeStorage={get(key){try{return localStorage.getItem(key)}catch{return null}},set(key,value){try{localStorage.setItem(key,value);return true}catch{return false}}}" in HTML
    assert "lang=safeStorage.get('vl-lang')||'fr'" in HTML

def test_save_failures_are_shown_instead_of_silently_ignored():
    assert "function showWorkspaceMessage" in HTML
    assert "Sauvegarde impossible" in HTML
    assert "Restore failed" in HTML

def test_html_ids_are_unique():
    parser = IdParser()
    parser.feed(HTML)
    duplicates = [item for item, count in Counter(parser.ids).items() if count > 1]
    assert not duplicates, f"Duplicate HTML ids: {duplicates}"

def test_api_version_is_38():
    assert '"version": "4.1"' in APP
    assert "v3.8 interface reliability" in APP
