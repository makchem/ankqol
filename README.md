# ankqol

Quality of life add-on for [Anki](https://apps.ankiweb.net/). Targets Anki 2.1.50+.

## Features

### Archive

Adds an **Archive** button to the top toolbar alongside Decks, Add, Browse, Stats, and Sync.

Archived decks are hidden from the main Decks view and only visible when the Archive tab is active. This is useful for decks you want to keep but aren't actively studying.

- Right-click any deck → **Archive Deck** to move it to the archive
- Right-click an archived deck → **Unarchive Deck** to restore it
- Archiving a parent deck automatically archives all its child decks

Archived deck IDs are stored in the add-on's own config and do not modify Anki's deck data.

### Featured Decks

Pin any number of decks to the top of the Decks list with a star marker.

- Click the **☆** icon next to any deck name to feature it — it turns gold **★** and the deck moves to the top
- Click the **★** again to unfeature it
- Or right-click any deck → **☆ Feature Deck** / **★ Unfeature Deck**
- Featuring a parent deck also features all its child decks
- Multiple decks can be featured simultaneously

Featured deck IDs are stored in the add-on's own config and do not modify Anki's deck data.

### Deck Rearrangement

Manually set the display order of decks in the Decks list.

- Click **☰ Rearrange decks** at the bottom of the Decks tab to open the rearrangement dialog
- The dialog shows two independent lists: **★ Featured** decks and regular **Decks**
- Regular decks list features a **Default** entry, which determines the position, at which the newly added decks will be positioned
- Drag items within each list to set the order, then click **OK** to apply
- Child decks always follow their parent — only top-level decks are listed
- The saved order persists across restarts

## Installation

Symlink or copy this repository folder into your Anki add-ons directory:

```
# Windows
mklink /J "%APPDATA%\Anki2\addons21\ankqol" "path\to\ankqol"

# macOS / Linux
ln -s /path/to/ankqol ~/Library/Application\ Support/Anki2/addons21/ankqol
```

Then restart Anki.

## Development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt  # Windows
# or
.venv/bin/pip install -r requirements-dev.txt       # macOS / Linux
```
