from __future__ import annotations

import json
from typing import Any, List, Tuple

from anki.decks import DeckId
from aqt import mw
from aqt.deckbrowser import DeckBrowser
from aqt.qt import QAction
from aqt.utils import tooltip

_active_tab: str = "decks"
_ADDON = "ankqol"


# ── Config helpers ────────────────────────────────────────────────────────────

def _get_archived() -> set[int]:
    config = mw.addonManager.getConfig(_ADDON) or {}
    return set(config.get("archived", []))


def _save_archived(ids: set[int]) -> None:
    config = mw.addonManager.getConfig(_ADDON) or {}
    config["archived"] = sorted(ids)
    mw.addonManager.writeConfig(_ADDON, config)


# ── Subtree helpers ───────────────────────────────────────────────────────────

def _subtree_ids(did: int) -> list[int]:
    if not mw.col:
        return []
    parent = mw.col.decks.get(DeckId(did))
    if not parent:
        return []
    prefix = parent["name"] + "::"
    return [d["id"] for d in mw.col.decks.all() if d["name"].startswith(prefix)]


# ── Archive / unarchive ───────────────────────────────────────────────────────

def archive_deck(did: int) -> None:
    ids = _get_archived()
    ids.add(did)
    ids.update(_subtree_ids(did))
    _save_archived(ids)
    mw.deckBrowser.show()
    mw.toolbar.draw()
    tooltip("Deck archived.")


def unarchive_deck(did: int) -> None:
    ids = _get_archived()
    ids.discard(did)
    for child_id in _subtree_ids(did):
        ids.discard(child_id)
    _save_archived(ids)
    mw.deckBrowser.show()
    mw.toolbar.draw()
    tooltip("Deck unarchived.")


# ── Filter JS (injected after deck browser renders) ───────────────────────────

_FILTER_JS = """
(function() {{
    var archived = new Set({archived_json});
    var tab = {tab_json};
    var rows = document.querySelectorAll('tr.deck[id]');
    var visible = 0;
    rows.forEach(function(row) {{
        var id = Number(row.id);
        var isArchived = archived.has(id);
        var show = (tab === 'decks') ? !isArchived : isArchived;
        row.style.display = show ? '' : 'none';
        if (show) visible++;
    }});
    var old = document.getElementById('ankqol-empty');
    if (old) old.remove();
    if (visible === 0 && tab === 'archive') {{
        var msg = document.createElement('p');
        msg.id = 'ankqol-empty';
        msg.style.cssText = 'text-align:center;color:#888;margin:2em 0;font-style:italic;';
        msg.textContent = 'No archived decks. Right-click any deck and choose "Archive Deck".';
        var tbl = document.querySelector('table');
        if (tbl) tbl.insertAdjacentElement('afterend', msg);
    }}
}})();
"""


# ── Hooks ─────────────────────────────────────────────────────────────────────

def on_toolbar_init_links(links: List[str], _toolbar: Any) -> None:
    active = _active_tab == "archive"
    style = ' style="font-weight:600;"' if active else ""
    link_html = (
        f'<a class=hitem tabindex="-1" aria-label="Archive" '
        f'title="View archived decks" href=# '
        f'onclick="return pycmd(\'ankqol:archive\')"{style}>Archive</a>'
    )
    # Insert after the first link (Decks)
    links.insert(1, link_html)


def on_did_render(deck_browser: DeckBrowser) -> None:
    archived = _get_archived()
    js = _FILTER_JS.format(
        archived_json=json.dumps(sorted(archived)),
        tab_json=json.dumps(_active_tab),
    )
    deck_browser.web.eval(js)


def on_options_menu(menu: Any, did: int) -> None:
    archived = _get_archived()
    menu.addSeparator()
    if did in archived:
        action = QAction("Unarchive Deck", menu)
        action.triggered.connect(lambda: unarchive_deck(did))
    else:
        action = QAction("Archive Deck", menu)
        action.triggered.connect(lambda: archive_deck(did))
    menu.addAction(action)


def on_js_message(
    handled: Tuple[bool, Any], message: str, _context: Any
) -> Tuple[bool, Any]:
    global _active_tab

    if message == "ankqol:archive":
        _active_tab = "archive"
        mw.deckBrowser.show()
        mw.toolbar.draw()
        return (True, None)

    # Reset archive state when user explicitly clicks Decks
    if message == "decks" and _active_tab == "archive":
        _active_tab = "decks"
        mw.toolbar.draw()
        return handled  # let Anki handle the navigation normally

    return handled
