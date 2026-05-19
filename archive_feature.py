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


def _get_featured() -> set[int]:
    config = mw.addonManager.getConfig(_ADDON) or {}
    return set(config.get("featured", []))


def _save_featured(ids: set[int]) -> None:
    config = mw.addonManager.getConfig(_ADDON) or {}
    config["featured"] = sorted(ids)
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


# ── Feature / unfeature ───────────────────────────────────────────────────────

def feature_deck(did: int) -> None:
    ids = _get_featured()
    ids.add(did)
    ids.update(_subtree_ids(did))
    _save_featured(ids)
    mw.deckBrowser.show()
    tooltip("Deck featured.")


def unfeature_deck(did: int) -> None:
    ids = _get_featured()
    ids.discard(did)
    for child_id in _subtree_ids(did):
        ids.discard(child_id)
    _save_featured(ids)
    mw.deckBrowser.show()
    tooltip("Deck unfeatured.")


# ── Deck browser JS ───────────────────────────────────────────────────────────

_DECK_JS = """
(function() {{
    var archived      = new Set({archived_json});
    var featured      = new Set({featured_json});
    var featuredGroup = new Set({featured_group_json});
    var tab           = {tab_json};

    // 1. Archive filter
    var rows = Array.from(document.querySelectorAll('tr.deck[id]'));
    var visible = 0;
    rows.forEach(function(row) {{
        var id = Number(row.id);
        var isArchived = archived.has(id);
        var show = (tab === 'decks') ? !isArchived : isArchived;
        row.style.display = show ? '' : 'none';
        if (show) visible++;
    }});

    if (tab === 'decks') {{
        // 2. Star icons
        rows.forEach(function(row) {{
            if (row.style.display === 'none') return;
            var id = Number(row.id);
            var isFeatured = featured.has(id);
            var star = row.querySelector('.ankqol-star');
            if (!star) {{
                star = document.createElement('span');
                star.className = 'ankqol-star';
                star.style.cssText = 'cursor:pointer;margin-right:4px;font-size:1em;line-height:1;vertical-align:middle;';
                var nameLink = row.querySelector('td a');
                if (nameLink) nameLink.parentNode.insertBefore(star, nameLink);
            }}
            star.textContent = isFeatured ? '★' : '☆';
            star.style.color = isFeatured ? '#f5a623' : '#ccc';
            star.title = isFeatured ? 'Unfeature deck' : 'Feature deck';
            (function(rowId) {{
                star.onclick = function(e) {{
                    e.stopPropagation();
                    pycmd('ankqol:star:' + rowId);
                    return false;
                }};
            }})(id);
        }});

        // 3. Move featured rows (and their children) to the top
        if (featuredGroup.size > 0) {{
            var parent = rows.length ? rows[0].parentNode : null;
            if (parent) {{
                var toMove = rows.filter(function(r) {{ return featuredGroup.has(Number(r.id)); }});
                var anchor = rows.find(function(r)   {{ return !featuredGroup.has(Number(r.id)); }}) || null;
                toMove.forEach(function(r) {{ parent.insertBefore(r, anchor); }});
            }}
        }}
    }}

    // 4. Empty state for archive tab
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
    links.insert(1, link_html)


def on_did_render(deck_browser: DeckBrowser) -> None:
    archived = _get_archived()
    featured = _get_featured()

    featured_group: set[int] = set()
    for did in featured:
        featured_group.add(did)
        featured_group.update(_subtree_ids(did))

    js = _DECK_JS.format(
        archived_json=json.dumps(sorted(archived)),
        featured_json=json.dumps(sorted(featured)),
        featured_group_json=json.dumps(sorted(featured_group)),
        tab_json=json.dumps(_active_tab),
    )
    deck_browser.web.eval(js)


def on_options_menu(menu: Any, did: int) -> None:
    archived = _get_archived()
    featured = _get_featured()
    menu.addSeparator()

    if did in featured:
        act = QAction("★ Unfeature Deck", menu)
        act.triggered.connect(lambda: unfeature_deck(did))
    else:
        act = QAction("☆ Feature Deck", menu)
        act.triggered.connect(lambda: feature_deck(did))
    menu.addAction(act)

    if did in archived:
        act = QAction("Unarchive Deck", menu)
        act.triggered.connect(lambda: unarchive_deck(did))
    else:
        act = QAction("Archive Deck", menu)
        act.triggered.connect(lambda: archive_deck(did))
    menu.addAction(act)


def on_js_message(
    handled: Tuple[bool, Any], message: str, _context: Any
) -> Tuple[bool, Any]:
    global _active_tab

    if message == "ankqol:archive":
        _active_tab = "archive"
        mw.deckBrowser.show()
        mw.toolbar.draw()
        return (True, None)

    if message.startswith("ankqol:star:"):
        try:
            did = int(message[len("ankqol:star:"):])
        except ValueError:
            return handled
        if did in _get_featured():
            unfeature_deck(did)
        else:
            feature_deck(did)
        return (True, None)

    if message == "decks" and _active_tab == "archive":
        _active_tab = "decks"
        mw.toolbar.draw()
        return handled

    return handled
