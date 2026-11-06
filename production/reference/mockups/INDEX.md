# Recovered mockup boards

Source: `forms_verse mockups.html` (2548250 bytes, `95ca5d1386e98dd2…`)

Private design evidence, recovered from the bundled artifact. The mockup photography is not the author's scan and is not cleared for use.

| board | recovered page | frame | resources |
|---|---|---|---|
| A1 · Stack | `2a30bffa.html` | 540×675 | 5 |
| A2 · Page alone | `4ed58e8a.html` | 540×675 | 4 |
| A3 · One line | `a930cdc7.html` | 540×675 | 4 |
| A4 · Profile grid | `a36e8d58.html` | 390×590 | 3 |
| B1 · Two albums | `d28bc96d.html` | 1240×800 | 15 |
| B2 · Participant home screens | `e0a809ea.html` | 1300×900 | 9 |

Each page is a self-extracting HTML document. `resources/<short>/` contains the referenced images/scripts decoded for inspection. Open the HTML file directly in a browser; it does not need a server.

Recover with:

```sh
python3 production/tools/recover_mockups.py "<source>.html" production/reference/mockups
```
