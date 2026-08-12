from __future__ import annotations

import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}


BUILTIN_NUMFMTS = {
    0: "General",
    1: "0",
    2: "0.00",
    3: "#,##0",
    4: "#,##0.00",
    9: "0%",
    10: "0.00%",
    11: "0.00E+00",
    12: "# ?/?",
    13: "# ??/??",
    14: "m/d/yy",
    15: "d-mmm-yy",
    16: "d-mmm",
    17: "mmm-yy",
    18: "h:mm AM/PM",
    19: "h:mm:ss AM/PM",
    20: "h:mm",
    21: "h:mm:ss",
    22: "m/d/yy h:mm",
    37: "#,##0 ;(#,##0)",
    38: "#,##0 ;[Red](#,##0)",
    39: "#,##0.00;(#,##0.00)",
    40: "#,##0.00;[Red](#,##0.00)",
    45: "mm:ss",
    46: "[h]:mm:ss",
    47: "mmss.0",
    48: "##0.0E+0",
    49: "@",
}


def qname(prefix: str, local: str) -> str:
    return f"{{{NS[prefix]}}}{local}"


def attrs(elem: ET.Element | None) -> dict[str, str]:
    if elem is None:
        return {}
    out: dict[str, str] = {}
    for key, value in elem.attrib.items():
        local = key.split("}")[-1]
        out[local] = value
    return out


def color_info(elem: ET.Element | None) -> dict[str, str] | None:
    if elem is None:
        return None
    result = attrs(elem)
    return result or None


def visible_text(elem: ET.Element) -> str:
    return "".join(t.text or "" for t in elem.iter() if t.tag in {qname("s", "t"), qname("w", "t")})


def relation_map(zf: zipfile.ZipFile, rel_path: str) -> dict[str, str]:
    if rel_path not in zf.namelist():
        return {}
    root = ET.fromstring(zf.read(rel_path))
    return {rel.attrib["Id"]: rel.attrib["Target"] for rel in root.findall("rel:Relationship", NS)}


def resolve_part(base_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return str(PurePosixPath(base_part).parent.joinpath(target))


def parse_styles(zf: zipfile.ZipFile) -> dict:
    if "xl/styles.xml" not in zf.namelist():
        return {"num_formats": {}, "fonts": [], "fills": [], "borders": [], "cell_xfs": []}
    root = ET.fromstring(zf.read("xl/styles.xml"))
    custom_numfmts = {
        int(n.attrib["numFmtId"]): n.attrib.get("formatCode", "")
        for n in root.findall("s:numFmts/s:numFmt", NS)
    }
    all_numfmts = dict(BUILTIN_NUMFMTS)
    all_numfmts.update(custom_numfmts)

    fonts = []
    for font in root.findall("s:fonts/s:font", NS):
        fonts.append(
            {
                "name": (font.find("s:name", NS).attrib.get("val") if font.find("s:name", NS) is not None else None),
                "size": (font.find("s:sz", NS).attrib.get("val") if font.find("s:sz", NS) is not None else None),
                "bold": font.find("s:b", NS) is not None,
                "italic": font.find("s:i", NS) is not None,
                "underline": attrs(font.find("s:u", NS)) or (True if font.find("s:u", NS) is not None else False),
                "strike": font.find("s:strike", NS) is not None,
                "color": color_info(font.find("s:color", NS)),
                "family": attrs(font.find("s:family", NS)).get("val"),
                "scheme": attrs(font.find("s:scheme", NS)).get("val"),
            }
        )

    fills = []
    for fill in root.findall("s:fills/s:fill", NS):
        pattern = fill.find("s:patternFill", NS)
        gradient = fill.find("s:gradientFill", NS)
        if pattern is not None:
            fills.append(
                {
                    "type": "pattern",
                    "patternType": pattern.attrib.get("patternType"),
                    "fgColor": color_info(pattern.find("s:fgColor", NS)),
                    "bgColor": color_info(pattern.find("s:bgColor", NS)),
                }
            )
        elif gradient is not None:
            fills.append({"type": "gradient", **attrs(gradient)})
        else:
            fills.append({"type": "none"})

    borders = []
    for border in root.findall("s:borders/s:border", NS):
        border_out = {}
        for edge in ["left", "right", "top", "bottom", "diagonal", "vertical", "horizontal"]:
            edge_elem = border.find(f"s:{edge}", NS)
            if edge_elem is not None:
                border_out[edge] = {
                    "style": edge_elem.attrib.get("style"),
                    "color": color_info(edge_elem.find("s:color", NS)),
                }
        borders.append(border_out)

    cell_xfs = []
    for xf in root.findall("s:cellXfs/s:xf", NS):
        xf_attrs = attrs(xf)
        numfmt_id = int(xf_attrs.get("numFmtId", 0))
        cell_xfs.append(
            {
                **xf_attrs,
                "numFmtCode": all_numfmts.get(numfmt_id),
                "alignment": attrs(xf.find("s:alignment", NS)),
                "protection": attrs(xf.find("s:protection", NS)),
            }
        )

    return {
        "num_formats": {str(k): v for k, v in sorted(all_numfmts.items())},
        "fonts": fonts,
        "fills": fills,
        "borders": borders,
        "cell_xfs": cell_xfs,
    }


def is_date_format(code: str | None) -> bool:
    if not code:
        return False
    scrubbed = re.sub(r'"[^"]*"|\\.|\[[^\]]*\]', "", code.lower())
    return bool(re.search(r"[dmyhs]", scrubbed))


def excel_date(value: str, date1904: bool) -> str | None:
    try:
        serial = float(value)
    except (TypeError, ValueError):
        return None
    origin = datetime(1904, 1, 1) if date1904 else datetime(1899, 12, 30)
    dt = origin + timedelta(days=serial)
    return dt.isoformat(sep=" ")


def shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return [visible_text(si) for si in root.findall("s:si", NS)]


def decode_cell(cell: ET.Element, strings: list[str], styles: dict, date1904: bool) -> dict:
    ref = cell.attrib.get("r")
    style_id = int(cell.attrib.get("s", 0))
    cell_type = cell.attrib.get("t", "n")
    formula_elem = cell.find("s:f", NS)
    value_elem = cell.find("s:v", NS)
    inline_elem = cell.find("s:is", NS)
    raw = value_elem.text if value_elem is not None else None
    formula = formula_elem.text if formula_elem is not None else None

    value = raw
    if cell_type == "s" and raw is not None:
        try:
            value = strings[int(raw)]
        except (IndexError, ValueError):
            value = raw
    elif cell_type == "inlineStr" and inline_elem is not None:
        value = visible_text(inline_elem)
    elif cell_type == "b" and raw is not None:
        value = raw == "1"
    elif cell_type == "n" and raw is not None:
        try:
            number = float(raw)
            value = int(number) if number.is_integer() else number
        except ValueError:
            value = raw

    style = styles.get("cell_xfs", [])[style_id] if style_id < len(styles.get("cell_xfs", [])) else {}
    date_value = excel_date(raw, date1904) if raw is not None and cell_type == "n" and is_date_format(style.get("numFmtCode")) else None
    out = {"ref": ref, "style": style_id, "type": cell_type, "value": value}
    if formula is not None:
        out["formula"] = formula
        out["formula_attrs"] = attrs(formula_elem)
        out["cached"] = raw
    if date_value is not None:
        out["date_iso"] = date_value
    return out


def parse_xlsx(path: Path) -> dict:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = relation_map(zf, "xl/_rels/workbook.xml.rels")
        styles = parse_styles(zf)
        strings = shared_strings(zf)
        workbook_pr = workbook.find("s:workbookPr", NS)
        date1904 = bool(workbook_pr is not None and workbook_pr.attrib.get("date1904") in {"1", "true"})
        sheets = []
        for sheet_node in workbook.findall("s:sheets/s:sheet", NS):
            name = sheet_node.attrib.get("name", "")
            rel_id = sheet_node.attrib.get(qname("r", "id"))
            target = rels.get(rel_id or "", "")
            part = resolve_part("xl/workbook.xml", target) if target else ""
            sheet_out = {"name": name, "state": sheet_node.attrib.get("state", "visible"), "part": part}
            if part not in names:
                sheets.append(sheet_out)
                continue
            root = ET.fromstring(zf.read(part))
            dimension = root.find("s:dimension", NS)
            sheet_out["dimension"] = dimension.attrib.get("ref") if dimension is not None else None
            view = root.find("s:sheetViews/s:sheetView", NS)
            sheet_out["view"] = attrs(view)
            panes = root.findall("s:sheetViews/s:sheetView/s:pane", NS)
            sheet_out["panes"] = [attrs(p) for p in panes]
            selections = root.findall("s:sheetViews/s:sheetView/s:selection", NS)
            sheet_out["selections"] = [attrs(s) for s in selections]
            sheet_format = root.find("s:sheetFormatPr", NS)
            sheet_out["sheet_format"] = attrs(sheet_format)
            sheet_out["columns"] = [attrs(c) for c in root.findall("s:cols/s:col", NS)]
            rows = []
            cells = []
            style_usage: Counter[int] = Counter()
            for row in root.findall("s:sheetData/s:row", NS):
                row_attrs = attrs(row)
                row_cells = []
                for cell in row.findall("s:c", NS):
                    decoded = decode_cell(cell, strings, styles, date1904)
                    cells.append(decoded)
                    row_cells.append(decoded["ref"])
                    style_usage[decoded["style"]] += 1
                rows.append({**row_attrs, "cells": row_cells})
            sheet_out["rows"] = rows
            sheet_out["cells"] = cells
            sheet_out["style_usage"] = {str(k): v for k, v in sorted(style_usage.items())}
            sheet_out["merges"] = [m.attrib.get("ref") for m in root.findall("s:mergeCells/s:mergeCell", NS)]
            sheet_out["hyperlinks"] = [attrs(h) for h in root.findall("s:hyperlinks/s:hyperlink", NS)]
            sheet_out["conditional_formats"] = [attrs(c) for c in root.findall("s:conditionalFormatting", NS)]
            validations = root.find("s:dataValidations", NS)
            sheet_out["data_validations"] = [attrs(v) for v in root.findall("s:dataValidations/s:dataValidation", NS)]
            sheet_out["auto_filter"] = attrs(root.find("s:autoFilter", NS))
            sheet_out["page_margins"] = attrs(root.find("s:pageMargins", NS))
            sheet_out["page_setup"] = attrs(root.find("s:pageSetup", NS))
            sheet_out["print_options"] = attrs(root.find("s:printOptions", NS))
            sheet_out["header_footer"] = {
                child.tag.split("}")[-1]: child.text
                for child in list(root.find("s:headerFooter", NS) or [])
            }
            drawing = root.find("s:drawing", NS)
            sheet_out["drawing_rel_id"] = drawing.attrib.get(qname("r", "id")) if drawing is not None else None
            sheets.append(sheet_out)

        defined_names = []
        for node in workbook.findall("s:definedNames/s:definedName", NS):
            defined_names.append({**attrs(node), "value": node.text})

        props = {}
        if "docProps/core.xml" in names:
            core = ET.fromstring(zf.read("docProps/core.xml"))
            for child in list(core):
                props[child.tag.split("}")[-1]] = child.text

        return {
            "path": str(path),
            "size": path.stat().st_size,
            "date1904": date1904,
            "properties": props,
            "defined_names": defined_names,
            "styles": styles,
            "sheets": sheets,
            "package_parts": sorted(names),
        }


def parse_docx(path: Path) -> dict:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        root = ET.fromstring(zf.read("word/document.xml"))
        body = root.find("w:body", NS)
        paragraphs = []
        tables = []
        if body is not None:
            for child in list(body):
                if child.tag == qname("w", "p"):
                    text = visible_text(child)
                    ppr = child.find("w:pPr", NS)
                    style = ppr.find("w:pStyle", NS) if ppr is not None else None
                    paragraphs.append({"text": text, "style": attrs(style).get("val")})
                elif child.tag == qname("w", "tbl"):
                    rows = []
                    for tr in child.findall("w:tr", NS):
                        row = []
                        for tc in tr.findall("w:tc", NS):
                            paras = []
                            for p in tc.findall(".//w:p", NS):
                                text = visible_text(p)
                                if text:
                                    paras.append(text)
                            row.append("\n".join(paras))
                        rows.append(row)
                    tables.append(rows)

        headers = {}
        for name in sorted(n for n in names if re.fullmatch(r"word/header\d+\.xml", n)):
            headers[name] = visible_text(ET.fromstring(zf.read(name)))
        footers = {}
        for name in sorted(n for n in names if re.fullmatch(r"word/footer\d+\.xml", n)):
            footers[name] = visible_text(ET.fromstring(zf.read(name)))
        props = {}
        if "docProps/core.xml" in names:
            core = ET.fromstring(zf.read("docProps/core.xml"))
            for child in list(core):
                props[child.tag.split("}")[-1]] = child.text
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "properties": props,
            "paragraphs": paragraphs,
            "tables": tables,
            "headers": headers,
            "footers": footers,
            "package_parts": sorted(names),
        }


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: inspect_ooxml.py OUTPUT.json INPUT.xlsx|docx [...]")
    output = Path(sys.argv[1])
    reports = []
    for raw in sys.argv[2:]:
        path = Path(raw)
        if path.suffix.lower() == ".xlsx":
            reports.append({"kind": "xlsx", **parse_xlsx(path)})
        elif path.suffix.lower() == ".docx":
            reports.append({"kind": "docx", **parse_docx(path)})
        else:
            raise ValueError(f"unsupported input: {path}")
    output.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
