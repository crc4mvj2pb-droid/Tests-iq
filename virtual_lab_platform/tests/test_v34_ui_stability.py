from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def test_electrical_catalog_category_is_available():
    assert 'data-cat="electrical"' in HTML
    assert "id:'resistor',cat:'electrical'" in HTML
    assert 'data-add="${x.id}"' in HTML


def test_catalogue_cards_use_textual_marks_not_item_emojis():
    assert "function catalogMark(x)" in HTML
    assert "esc(catalogMark(x))" in HTML
    assert 'class="wb-object-icon">RXN</span>' in HTML


def test_final_responsive_overrides_are_last_in_stylesheet():
    final_style = HTML.rsplit("<style>", 1)[1].split("</style>", 1)[0]
    assert "v3.4: final catalogue layout overrides" in final_style
    assert "grid-template-columns:minmax(320px,390px) minmax(0,1fr) minmax(270px,330px)" in final_style
    assert "@media(max-width:1250px)" in final_style
    assert "@media(max-width:760px)" in final_style
    assert final_style.index("v3.4: final catalogue layout overrides") > final_style.index(".wb-result th")


def test_catalogue_core_interactions_are_wired():
    assert "$('wbSearch').oninput=renderCatalog" in HTML
    assert "b.onclick=()=>addItem(b.dataset.add)" in HTML
    assert "el.addEventListener('dragstart'" in HTML
    assert "el.addEventListener('drop'" in HTML
    assert "$('wbDelete').onclick" in HTML


def test_api_version_is_bumped():
    assert '"version": "4.1"' in APP
