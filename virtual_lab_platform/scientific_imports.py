"""Safe local intake and provenance for scientific files. Imported SBML is not executed."""
from __future__ import annotations
import csv, hashlib, json, re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
ASSET_DIR = BASE / "scientific_library" / "imported_assets"
INDEX = ASSET_DIR / "index.json"
MAX_FILE_BYTES = 900_000
MAX_CSV_ROWS = 100_000

def _clean_filename(value: Any, fallback: str) -> str:
    if not isinstance(value, str): value = fallback
    name = Path(value.replace("\\\\", "/")).name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or fallback
    return name[:100]

def _load_index() -> dict:
    if not INDEX.exists(): return {"schema_version":"1.0","assets":[]}
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    if not isinstance(data.get("assets"), list): raise ValueError("Imported-assets registry is malformed.")
    return data

def list_assets() -> dict:
    return _load_index()

def _save_asset(record: dict) -> None:
    data = _load_index()
    for old in data["assets"]:
        if old.get("sha256") == record["sha256"]:
            record["duplicate_of"] = old["id"]
            record["already_registered"] = True
            return
    data["assets"].append(record)
    tmp = INDEX.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(INDEX)

def import_sbml(filename: Any, content: Any, source_url: Any = "") -> dict:
    if not isinstance(content, str) or not content.strip(): raise ValueError("Provide the text content of an SBML/XML file.")
    raw = content.encode("utf-8")
    if len(raw) > MAX_FILE_BYTES: raise ValueError(f"SBML file exceeds the {MAX_FILE_BYTES}-byte import limit.")
    # v9.1: the whole text is checked (a long comment before the DOCTYPE bypassed the former 20 000-character check).
    import security
    if security.has_dtd(content): raise ValueError("DOCTYPE and ENTITY declarations are not accepted.")
    try: doc = ET.fromstring(raw)
    except ET.ParseError as exc: raise ValueError(f"Invalid XML/SBML: {exc}") from None
    if doc.tag.rsplit("}", 1)[-1] != "sbml": raise ValueError("The XML root element is not SBML.")
    model = next((e for e in doc.iter() if e.tag.rsplit("}",1)[-1] == "model"), None)
    if model is None: raise ValueError("No model element was found in this SBML document.")
    def count(local): return sum(1 for e in model.iter() if e.tag.rsplit("}",1)[-1] == local)
    safe_name = _clean_filename(filename, "imported_model.xml")
    digest = hashlib.sha256(raw).hexdigest()
    asset_id = "sbml_" + digest[:16]
    target = ASSET_DIR / "models" / f"{asset_id}_{safe_name}"
    target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    record = {
      "id":asset_id,"type":"sbml_model","filename":safe_name,"stored_path":str(target.relative_to(BASE)),
      "sha256":digest,"size_bytes":len(raw),"imported_at":datetime.now(timezone.utc).isoformat(),
      "source_url":source_url.strip()[:1000] if isinstance(source_url,str) else "",
      "license":"unknown; verify original source terms",
      "metadata":{"model_name":model.attrib.get("name") or model.attrib.get("id") or safe_name,
        "model_id":model.attrib.get("id"),"sbml_level":doc.attrib.get("level"),"sbml_version":doc.attrib.get("version"),
        "compartment_count":count("compartment"),"species_count":count("species"),
        "reaction_count":count("reaction"),"parameter_count":count("parameter")},
      "execution_status":"stored_not_executed","validation_status":"xml_structure_checked_only_not_scientifically_validated"}
    _save_asset(record); return record

def import_dataset(filename: Any, content: Any, source_url: Any = "", description: Any = "") -> dict:
    if not isinstance(content,str) or not content.strip(): raise ValueError("Provide CSV dataset content.")
    raw=content.encode("utf-8")
    if len(raw)>MAX_FILE_BYTES: raise ValueError(f"Dataset exceeds the {MAX_FILE_BYTES}-byte import limit.")
    try:
        rows=csv.reader(content.lstrip("\\ufeff").splitlines())
        header=next(rows,None)
        if not header or not any(c.strip() for c in header): raise ValueError("CSV must have a header row.")
        header=[c.strip() for c in header]
        if len(set(header))!=len(header): raise ValueError("CSV headers must be unique.")
        row_count=0
        for row in rows:
            if not row or not any(cell.strip() for cell in row): continue
            if len(row)!=len(header): raise ValueError(f"CSV row {row_count+2} has {len(row)} columns; expected {len(header)}.")
            row_count+=1
            if row_count>MAX_CSV_ROWS: raise ValueError(f"Dataset exceeds the {MAX_CSV_ROWS}-row limit.")
    except UnicodeDecodeError: raise ValueError("CSV must be UTF-8 encoded.") from None
    if row_count==0: raise ValueError("CSV must contain at least one data row.")
    safe_name=_clean_filename(filename,"dataset.csv")
    if not safe_name.casefold().endswith(".csv"): safe_name += ".csv"
    digest=hashlib.sha256(raw).hexdigest(); asset_id="csv_"+digest[:16]
    target=ASSET_DIR/"datasets"/f"{asset_id}_{safe_name}"
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    record={"id":asset_id,"type":"reference_dataset","filename":safe_name,"stored_path":str(target.relative_to(BASE)),
      "sha256":digest,"size_bytes":len(raw),"imported_at":datetime.now(timezone.utc).isoformat(),
      "source_url":source_url.strip()[:1000] if isinstance(source_url,str) else "",
      "description":description.strip()[:2000] if isinstance(description,str) else "",
      "license":"unknown; verify original source terms",
      "metadata":{"columns":header,"row_count":row_count},"execution_status":"stored_not_used_in_analysis",
      "validation_status":"csv_structure_checked_only_values_not_scientifically_validated"}
    _save_asset(record); return record
