from __future__ import annotations

import json
from typing import Any, List, Tuple

from anki.decks import DeckId
from aqt import mw
from aqt.deckbrowser import DeckBrowser
from aqt.qt import (
    QAction, QDialog, QDialogButtonBox, QLabel,
    QListWidget, QListWidgetItem, Qt, QVBoxLayout,
)
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


def _get_order() -> list[int]:
    config = mw.addonManager.getConfig(_ADDON) or {}
    return config.get("order", [])


def _save_order(order: list[int]) -> None:
    config = mw.addonManager.getConfig(_ADDON) or {}
    config["order"] = order
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


# ── Rearrange dialog ──────────────────────────────────────────────────────────

def _make_list() -> QListWidget:
    lw = QListWidget()
    lw.setDragDropMode(QListWidget.DragDropMode.InternalMove)
    lw.setDefaultDropAction(Qt.DropAction.MoveAction)
    return lw


def _list_ids(lw: QListWidget) -> list[int]:
    ids = []
    for i in range(lw.count()):
        item = lw.item(i)
        if item is not None:
            ids.append(item.data(Qt.ItemDataRole.UserRole))
    return ids


class RearrangeDialog(QDialog):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Rearrange Decks")
        self.setMinimumWidth(360)
        self.setMinimumHeight(500)

        layout = QVBoxLayout(self)

        hint = QLabel("Drag decks to set their display order. Child decks follow their parent automatically.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.featured_list = _make_list()
        self.normal_list   = _make_list()

        featured_label = QLabel("★ Featured")
        featured_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(featured_label)
        layout.addWidget(self.featured_list)

        normal_label = QLabel("Decks")
        normal_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
        layout.addWidget(normal_label)
        layout.addWidget(self.normal_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        if not mw.col:
            return
        archived = _get_archived()
        featured = _get_featured()
        order    = _get_order()

        top_decks = [
            d for d in mw.col.decks.all()
            if "::" not in d["name"] and d["id"] not in archived
        ]

        def sort_key(d: Any) -> int:
            try:
                return order.index(d["id"])
            except ValueError:
                return len(order)

        top_decks.sort(key=sort_key)

        for deck in top_decks:
            item = QListWidgetItem(deck["name"])
            item.setData(Qt.ItemDataRole.UserRole, deck["id"])
            if deck["id"] in featured:
                self.featured_list.addItem(item)
            else:
                self.normal_list.addItem(item)

    def get_order(self) -> list[int]:
        return _list_ids(self.featured_list) + _list_ids(self.normal_list)


def open_rearrange_dialog() -> None:
    dialog = RearrangeDialog(mw)
    if dialog.exec():
        _save_order(dialog.get_order())
        mw.deckBrowser.show()
        tooltip("Deck order saved.")


# ── Deck browser JS ───────────────────────────────────────────────────────────

_DECK_JS = """
(function() {{
    var archived    = new Set({archived_json});
    var featured    = new Set({featured_json});
    var deckLevels  = {deck_levels_json};
    var customOrder = {custom_order_json};
    var tab         = {tab_json};

    /* ── 1. Archive filter ───────────────────────────────────────────────── */
    var allRows = Array.from(document.querySelectorAll('tr.deck[id]'));
    var visible = 0;
    allRows.forEach(function(row) {{
        var id = Number(row.id);
        var isArchived = archived.has(id);
        var show = (tab === 'decks') ? !isArchived : isArchived;
        row.style.display = show ? '' : 'none';
        if (show) visible++;
    }});

    if (tab === 'decks') {{
        var rows = allRows.filter(function(r) {{ return r.style.display !== 'none'; }});

        /* ── 2. Build groups (top-level deck + its child rows) ───────────── */
        var groups = [];
        var cur = null;
        rows.forEach(function(row) {{
            var id    = Number(row.id);
            var level = deckLevels[id] !== undefined ? deckLevels[id] : 0;
            if (level === 0) {{
                cur = {{id: id, rows: [row]}};
                groups.push(cur);
            }} else if (cur) {{
                cur.rows.push(row);
            }}
        }});

        /* ── 3. Sort groups: featured first, non-featured below ──────────── */
        function sortByOrder(list) {{
            if (!customOrder.length) return list.slice();
            return list.slice().sort(function(a, b) {{
                var ia = customOrder.indexOf(a.id);
                var ib = customOrder.indexOf(b.id);
                if (ia === -1 && ib === -1) return 0;
                if (ia === -1) return 1;
                if (ib === -1) return -1;
                return ia - ib;
            }});
        }}
        var featuredGroups = groups.filter(function(g) {{ return  featured.has(g.id); }});
        var normalGroups   = groups.filter(function(g) {{ return !featured.has(g.id); }});
        var sorted = sortByOrder(featuredGroups).concat(sortByOrder(normalGroups));

        if (sorted.length) {{
            var tbody = sorted[0].rows[0].parentNode;
            sorted.forEach(function(g) {{
                g.rows.forEach(function(r) {{ tbody.appendChild(r); }});
            }});
        }}

        /* ── 4. Star icons ───────────────────────────────────────────────── */
        groups.forEach(function(group) {{
            group.rows.forEach(function(row) {{
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
                star.style.color  = isFeatured ? '#f5a623' : '#ccc';
                star.title        = isFeatured ? 'Unfeature deck' : 'Feature deck';
                (function(rid) {{
                    star.onclick = function(e) {{
                        e.stopPropagation();
                        pycmd('ankqol:star:' + rid);
                        return false;
                    }};
                }})(id);
            }});
        }});
    }}

    /* ── 5. Empty state (archive tab) ───────────────────────────────────── */
    var old = document.getElementById('ankqol-empty');
    if (old) old.remove();
    if (visible === 0 && tab === 'archive') {{
        var msg = document.createElement('p');
        msg.id  = 'ankqol-empty';
        msg.style.cssText = 'text-align:center;color:#888;margin:2em 0;font-style:italic;';
        msg.textContent   = 'No archived decks. Right-click any deck and choose "Archive Deck".';
        var tbl = document.querySelector('table');
        if (tbl) tbl.insertAdjacentElement('afterend', msg);
    }}
}})();
"""


# ── Hooks ─────────────────────────────────────────────────────────────────────

def on_toolbar_init_links(links: List[str], _toolbar: Any) -> None:
    active = _active_tab == "archive"
    style  = ' style="font-weight:600;"' if active else ""
    archive_link = (
        f'<a class=hitem tabindex="-1" aria-label="Archive" '
        f'title="View archived decks" href=# '
        f'onclick="return pycmd(\'ankqol:archive\')"{style}>Archive</a>'
    )
    links.insert(1, archive_link)


def on_will_render_content(_deck_browser: DeckBrowser, content: Any) -> None:
    if _active_tab != "decks":
        return
    button_html = (
        '<div style="text-align:right;padding:6px 4px 0;">'
        '<a href=# onclick="return pycmd(\'ankqol:rearrange\')" '
        'style="font-size:0.85em;color:#888;text-decoration:none;">'
        '&#9776; Rearrange decks</a>'
        '</div>'
    )
    content.tree += button_html


def on_did_render(deck_browser: DeckBrowser) -> None:
    archived = _get_archived()
    featured = _get_featured()
    order    = _get_order()

    deck_levels: dict[int, int] = {}
    if mw.col:
        for d in mw.col.decks.all():
            deck_levels[d["id"]] = d["name"].count("::")

    js = _DECK_JS.format(
        archived_json     = json.dumps(sorted(archived)),
        featured_json     = json.dumps(sorted(featured)),
        deck_levels_json  = json.dumps(deck_levels),
        custom_order_json = json.dumps(order),
        tab_json          = json.dumps(_active_tab),
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

    if message == "ankqol:rearrange":
        open_rearrange_dialog()
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
