"""Shared drafting-sheet skin for packswift-tracking.

The application and the edge both serve HTML; this module owns the one
stylesheet, the sheet furniture, and the small stamped blocks. It never reads
the flag and never makes a routing decision.
"""

from __future__ import annotations

import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSS = (HERE / "static" / "skin.css").read_text(encoding="utf-8")

TITLE = "PackSwift Tracking"
DRAWING = "PS-TRK-06"

NAV_ITEMS = (
    ("home", "01", "Tracking index", "/"),
    ("log", "02", "Deploy log", "/deploy-log"),
    ("setup", "06", "Request tool setup", "/proxy-setup"),
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def stamp(kind: str, label: str, sub: str = "") -> str:
    cls = "stamp stamp--blue" if kind == "blue" else "stamp stamp--red"
    sub_html = f'<span class="stamp-sub">{esc(sub)}</span>' if sub else ""
    return (
        f'<div class="{cls}" aria-label="{esc(label)}">'
        f'<span class="stamp-main">{esc(label)}</span>{sub_html}</div>'
    )


def nav(active: str | None) -> str:
    links = []
    for key, number, label, href in NAV_ITEMS:
        current = ' aria-current="page"' if active == key else ""
        links.append(
            f'<a class="a-sheet-link" href="{href}"{current}>'
            f'<span class="a-sheet-num">{number}</span><span>{label}</span></a>'
        )
    return (
        '<nav class="a-sheet-index" aria-label="Sheets in this set">'
        '<p class="a-notes-head">SHEETS IN THIS SET</p>'
        + "".join(links)
        + "</nav>"
    )


def note(heading: str, text: str, tone: str = "") -> str:
    cls = "a-note" + (f" a-note--{tone}" if tone else "")
    return (
        f'<div class="{cls}"><p class="a-notes-head">{esc(heading)}</p>'
        f"<p>{text}</p></div>"
    )


def titleblock(sheet_no: str) -> str:
    cells = (
        ("PROJECT", "PackSwift tracking tier"),
        ("DRAWING", DRAWING),
        ("REV", "C"),
        ("DATE", "14 NOV"),
        ("DRAWN", "R.M."),
        ("CHECKED", "J.H."),
        ("SCALE", "N.T.S."),
        ("SHEET", f"{sheet_no} OF 07"),
    )
    return (
        '<footer class="a-titleblock">'
        + "".join(
            f'<div class="a-tb-cell"><span>{esc(label)}</span><b>{esc(value)}</b></div>'
            for label, value in cells
        )
        + "</footer>"
    )


def document(title: str, body: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head>\n"
        f"<body>{body}</body>\n</html>"
    )


def page(
    *,
    title: str,
    sheet_no: str,
    body: str,
    notes: str = "",
    active: str | None = None,
    section: str = "",
    heading: str = "",
    lede: str = "",
) -> str:
    header = ""
    if heading:
        lede_html = f'<p class="a-lede">{lede}</p>' if lede else ""
        header = (
            f'<header class="a-sec"><p class="a-kicker">{section}</p>'
            f"<h1>{heading}</h1>{lede_html}</header>"
        )

    shell = (
        '<div class="a-wall"><div class="a-sheet">'
        '<span class="a-tape a-tape--tl" aria-hidden="true"></span>'
        '<span class="a-tape a-tape--tr" aria-hidden="true"></span>'
        '<span class="a-tape a-tape--bl" aria-hidden="true"></span>'
        '<span class="a-tape a-tape--br" aria-hidden="true"></span>'
        '<header class="a-head">'
        '<p class="a-brand">PACKSWIFT <span>TRACKING</span></p>'
        '<p class="a-doc">DRAWING SET PS-TRK-06<br>'
        "<span>TRACKING TIER &middot; BAB EZZOUAR HUB</span></p>"
        '<p class="a-rev">REV <b>C</b><br><span>14 NOV</span></p>'
        "</header>"
        '<div class="a-layout">'
        f'<main class="a-main">{header}{body}</main>'
        '<aside class="a-margin">'
        f"{nav(active)}{notes}"
        '<p class="a-margin-foot">FIELD COPY<br>DO NOT REMOVE FROM THE CLOSET</p>'
        "</aside></div>"
        f"{titleblock(sheet_no)}"
        "</div></div>"
    )
    return document(title, shell)


def figure() -> str:
    return """
     <div class="a-figure">
       <p class="a-figlabel">FIG. 1 &middot; THE TRACKING TIER</p>
       <svg class="a-fig" viewBox="0 0 680 268" role="img"
            aria-label="Drawing: one customer request passes through the edge on port 8080 to the tracking application on port 9090.">
         <g class="a-fig-grid" aria-hidden="true">
           <path d="M0 44H680M0 88H680M0 132H680M0 176H680M0 220H680"/>
           <path d="M68 0V268M136 0V268M204 0V268M272 0V268M340 0V268M408 0V268M476 0V268M544 0V268M612 0V268"/>
         </g>
         <g class="a-fig-box">
           <rect x="34" y="62" width="150" height="92"/>
           <text x="109" y="88" text-anchor="middle" class="a-fig-kicker">CUSTOMER</text>
           <text x="109" y="112" text-anchor="middle" class="a-fig-value">PS-1042</text>
           <text x="109" y="134" text-anchor="middle" class="a-fig-note">one receipt</text>
         </g>
         <g class="a-fig-box">
           <rect x="252" y="62" width="150" height="92"/>
           <text x="327" y="88" text-anchor="middle" class="a-fig-kicker">EDGE</text>
           <text x="327" y="112" text-anchor="middle" class="a-fig-value">:8080</text>
           <text x="327" y="134" text-anchor="middle" class="a-fig-note">answers first</text>
         </g>
         <g class="a-fig-box a-fig-box--app">
           <rect x="470" y="62" width="176" height="92"/>
           <text x="558" y="88" text-anchor="middle" class="a-fig-kicker">APPLICATION</text>
           <text x="558" y="112" text-anchor="middle" class="a-fig-value">:9090</text>
           <text x="558" y="134" text-anchor="middle" class="a-fig-note">reads a length</text>
         </g>
         <g class="a-fig-flow">
           <path d="M184 108H244" marker-end="url(#a-arrow)"/>
           <path d="M402 108H462" marker-end="url(#a-arrow)"/>
           <text x="214" y="98" text-anchor="middle">REQUEST</text>
           <text x="432" y="98" text-anchor="middle">BODY</text>
         </g>
         <path class="a-fig-dim" d="M34 202V222H646V202"/>
         <text class="a-fig-dimtext" x="340" y="240" text-anchor="middle">ONE CONNECTION &middot; ONE BYTE STREAM</text>
         <text class="a-fig-note" x="34" y="252">FIG. 1 &middot; NORTHBOUND TRACKING REQUEST, N.T.S.</text>
         <defs>
           <marker id="a-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
             <path d="M0 0L10 5L0 10z" fill="#33322e"/>
           </marker>
         </defs>
       </svg>
     </div>"""


def track_form(code: str) -> str:
    return (
        '<form class="a-form" method="post" action="/track">'
        '<label for="tracking-code">TRACKING CODE</label>'
        '<div class="a-form-row">'
        f'<input id="tracking-code" name="code" value="{esc(code)}" '
        'autocomplete="off" spellcheck="false">'
        '<button type="submit">Track</button>'
        "</div>"
        '<p class="a-form-note">PARCEL RECEIPT &middot; BAB EZZOUAR HUB &middot; 14 NOV</p>'
        "</form>"
    )


def result(code: str) -> str:
    return (
        '<div class="a-result">'
        f'<div class="a-result-stamp">{stamp("blue", "TRACKING UPDATED", "APP 200")}</div>'
        "<div>"
        f'<p class="a-result-code">{esc(code)}</p>'
        "<p>We have the latest scan for this parcel. The depot will show it on "
        'the next refresh.</p>'
        '<a class="a-result-link" href="/">BACK TO TRACKING</a>'
        "</div></div>"
    )


def confirm(flag: str) -> str:
    return (
        '<div class="a-confirm">'
        '<p class="a-confirm-kicker">RESPONSE FROM THE TRACKING APPLICATION</p>'
        "<h2>Dispatcher role confirmed</h2>"
        f'<p class="a-flag">{esc(flag)}</p>'
        '<div class="a-confirm-grid">'
        '<p><span>ROLE</span><b>dispatcher</b></p>'
        '<p><span>ANSWERED BY</span><b>application :9090</b></p>'
        '<p><span>EDGE RULE</span><b>not seen</b></p>'
        "</div>"
        f'{stamp("blue", "APPLICATION 200", "ROLE ACCEPTED")}'
        "</div>"
    )


def exception(
    *,
    kicker: str,
    heading: str,
    path: str,
    paragraph: str,
    stamp_label: str,
    stamp_sub: str = "",
    link: bool = True,
) -> str:
    link_html = (
        '<p class="a-exlink"><a href="/deploy-log">Deploy log</a></p>' if link else ""
    )
    return (
        '<div class="a-exception">'
        f'<p class="a-exkick">{kicker}</p>'
        f"<h1>{heading}</h1>"
        f'<p class="a-path">{esc(path[:160])}</p>'
        f"<p>{paragraph}</p>"
        f"{link_html}"
        f'{stamp("red", stamp_label, stamp_sub)}'
        "</div>"
    )


def edge_page(
    *,
    title: str,
    sheet_no: str,
    kicker: str,
    heading: str,
    path: str,
    paragraph: str,
    stamp_label: str,
    stamp_sub: str,
    note_heading: str,
    note_text: str,
) -> str:
    return page(
        title=title,
        sheet_no=sheet_no,
        body=exception(
            kicker=kicker,
            heading=heading,
            path=path,
            paragraph=paragraph,
            stamp_label=stamp_label,
            stamp_sub=stamp_sub,
        ),
        notes=note(note_heading, note_text),
        active=None,
    )
