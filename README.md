# nida

A Python library and desktop app for looking up Tanzanian National ID (NIDA)
holders by their 20-digit National Identification Number.

```
mashimi-nida/
├── app.py                  # desktop UI entry point
├── streamlit_app.py        # optional browser UI
├── nida/                   # the library
│   ├── __init__.py
│   └── exceptions.py
├── nidaui/                 # the app's custom tkinter widget kit
│   ├── theme.py            #   palettes, fonts, spacing tokens
│   ├── draw.py             #   rounded-rectangle / colour helpers
│   ├── base.py             #   ThemedFrame + theme application
│   ├── card.py             #   Card, Badge
│   ├── buttons.py          #   Button, IconButton, Tooltip
│   ├── fields.py           #   Field
│   ├── containers.py       #   ScrollFrame, Scrollbar, ListRow
│   ├── panels.py           #   lookup + history panels
│   ├── profile.py          #   record panel
│   ├── history.py          #   local JSON cache
│   ├── demo.py             #   offline sample records
│   └── app.py              #   app shell
├── tests/test_nida.py
├── setup.py
├── requirements.txt
└── LICENSE
```

## Can you get a NIDA number from a name?

**No — not with this API.** The endpoint the package uses
(`ors.brela.go.tz/um/load/load_nida/{NIN}`) works in one direction only: you
supply a 20-digit ID and get that person's details back. NIDA publishes no
"search people by name" service, deliberately, for privacy reasons.

What this project does instead:

- ✅ **NIN → full details** (live, from NIDA)
- ✅ **Name → NIN**, but only for records this machine has already fetched;
  every lookup is cached to `nida_history.json` so you can search your own
  history afterwards.

A genuine name→NIN search would require an official agreement with
NIDA/BRELA.

> Only look up IDs you have permission or consent to check — this returns real
> personal data.

## Install

```bash
pip install -r requirements.txt
```

## Run the desktop app

```bash
python app.py            # live lookups against NIDA
python app.py --demo     # offline preview with generated sample records
```

`--demo` is handy for trying the interface without hitting the government
service; it seeds four fictional people and never sends a request.

### The interface

- **Look up a person** — enter the NIN, press Fetch (or `Ctrl+F`).
- **Search your history** — free-text search over cached records; click a row
  to reopen it.
- **Record** — photo, name, grouped fields, signature, and save buttons. Click
  any value to copy it.

| Shortcut | Action |
|---|---|
| `Ctrl+L` | Focus the NIN field |
| `Ctrl+F` | Re-fetch the current NIN |
| `Ctrl+T` | Toggle dark / light theme |
| `Esc` | Clear the NIN field |
| `Enter` | Submit, from either input |

Fetches run on a worker thread, so the window never freezes; results are
handed back to the Tk main loop through a queue. The status bar at the bottom
reports progress and errors with a colour-coded indicator.

## Run the web UI instead

```bash
pip install streamlit
streamlit run streamlit_app.py
```

## Library use

```python
from nida import load_user

user = load_user("19990512141150000123")
print(user.Fullname, user.Gender)
user.Photo.save("photo.jpg")          # PHOTO/SIGNATURE arrive as PIL images
```

Or keep the raw payload:

```python
raw = load_user("19990512141150000123", as_json=True)
```

Customise the client with a timeout:

```python
from nida import Nida

client = Nida(timeout=30)
user = client.load_user(19990512141150000123)
```

### Errors

All failures raise subclasses of `NidaError`:

| Exception | Raised when |
|---|---|
| `NidaInvalidIDError` | the ID is not exactly 20 digits |
| `NidaNotFoundError` | NIDA has no record for that ID |
| `NidaConnectionError` | the request timed out or the network failed |
| `NidaError` | the response was not JSON, or was otherwise unexpected |

## Tests

```bash
python -m unittest discover -s tests -v
```

The suite mocks `requests.post`, so it never touches the network.

## Linux note

If you get `ImportError: ImageTk`, install the tkinter imaging add-on:

```bash
sudo apt install python3-pil.imagetk
```

## License

MIT — see [LICENSE](LICENSE).
