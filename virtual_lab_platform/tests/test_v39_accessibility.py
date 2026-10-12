from pathlib import Path
from collections import Counter
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.categories=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if a.get("id"): self.ids.append(a["id"])
        if a.get("data-cat"): self.categories.append((a["data-cat"],a.get("aria-pressed")))

def test_api_reports_v39():
    assert '"version": "4.1"' in APP
    assert 'v3.9 accessibility' in APP

def test_all_library_categories_have_explicit_initial_pressed_state():
    parser=IdParser(); parser.feed(HTML)
    cats=dict(parser.categories)
    assert set(cats) >= {"equipment","substances","molecules","biology","physics","electrical","reactions","tools"}
    assert cats["equipment"] == "true"
    assert all(cats[c] == "false" for c in cats if c != "equipment")
    assert "q.setAttribute('aria-pressed',String(q===b))" in HTML

def test_workbench_items_can_be_selected_with_enter_and_space():
    assert 'tabindex="0" role="group" aria-label=' in HTML
    assert "card.addEventListener('keydown'" in HTML
    assert "e.key==='Enter'||e.key===' '" in HTML
    assert 'document.querySelector(`[data-instance=\\"${focusId}\\"]`)?.focus()' in HTML

def test_keyboard_focus_is_visible_and_library_search_is_named():
    assert 'button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible' in HTML
    assert 'aria-label="Rechercher dans la bibliothèque"' in HTML

def test_library_and_inspector_announce_dynamic_updates():
    assert 'id="wbCatalog" class="wb-catalog" aria-live="polite"' in HTML
    assert 'id="wbInspector" class="wb-inspector-body" aria-live="polite"' in HTML

def test_html_ids_remain_unique():
    parser=IdParser(); parser.feed(HTML)
    duplicates=[i for i,n in Counter(parser.ids).items() if n>1]
    assert not duplicates, f"Duplicate IDs: {duplicates}"
