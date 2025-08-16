# Mock Draft Simulator 2025 - Web Version

## How to Run

1. **Open directly in browser:**
   - Simply double-click on `index.html` to open in your default browser
   - Or right-click `index.html` and choose "Open with" → Your preferred browser

2. **Using a local server (recommended for best performance):**
   ```bash
   # If you have Python installed:
   python3 -m http.server 8000
   # Then open http://localhost:8000 in your browser
   
   # Or with Node.js:
   npx http-server
   ```

## Features

This is a static web version of the Mock Draft Simulator that runs entirely in your browser. It includes:

- **Draft Board**: Visual representation of all draft picks
- **Player List**: Sortable/filterable list of available players
- **Custom ADP**: Click on ADP values to edit them
- **Draft Spot Selection**: Choose your team position
- **Auto-Draft**: Computer teams make intelligent picks
- **Trade System**: Trade draft picks between teams
- **Dark Theme**: Matches the desktop version's appearance
- **Local Storage**: Your custom ADP values and drafts are saved locally

## Browser Compatibility

Works best in modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Notes

- All data is stored locally in your browser
- No server or internet connection required after initial load
- Custom ADP values persist between sessions
- Draft progress can be saved and loaded later