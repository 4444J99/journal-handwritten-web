# Photos / album / widget device test — 2026-11-06

## What was tested here

Environment: macOS 26.7.2 (build 25G320), Apple M5, 16 GB, no Xcode. No iPhone, no iOS Simulator (`xcrun simctl` unavailable), no `cliclick`/GUI automation. `screencapture` works for full-screen images but cannot drive the UI, so no widget render was performed.

Static evidence collected:

- Photos widget extension installed at:
  `/System/Applications/Photos.app/Contents/PlugIns/PhotosReliveWidget.appex`
- Extension identifier `PhotosReliveWidgetAlbum`; class `PhotoReliveWidgetAlbumOptionsProvider`.
- Localised English strings, from
  `PhotosReliveWidget.appex/Contents/Resources/PhotosReliveWidget.loctable`:
  - `PHOTOS_RELIVE_WIDGET_COLLECTIONS_DISPLAY_NAME` = **Album**
  - `PHOTOS_RELIVE_WIDGET_COLLECTIONS_DESCRIPTION` =
    "Choose an album to shuffle throughout the day."
  - `PHOTOS_WIDGET_ALBUM_PROPERTY_TITLE` = **Album**
  - `PHOTOS_WIDGET_ALBUM_PICKER_PROMPT` = **Select Album**
  - `PHOTOS_WIDGET_ALBUM_TYPE_USER` = **My Albums**
  - `PHOTOS_WIDGET_ALBUM_TYPE_SMART` = **Smart Albums**
- Album types advertised by the extension: user albums and smart albums. **Shared albums are not advertised** in the localised strings; `unexpected smart album type` is the only album-type error logged.
- The signed-in Photos library contains these user albums (read via `osascript`, no mutation):
  `structure`, `alien`, `fitness`, `092126`, `Giphy`, `Dropbox`, `simvl-live`.
  No test album was created and no library mutation was made.
- `screencapture` succeeds, so a screenshot-based record is possible once the
  widget is rendered by hand.

## What was NOT tested

1. Importing the widget tiles into Photos.
2. Creating a test album and adding the tiles.
3. Adding the Photos widget to the macOS desktop / Notification Center / home
   screen and selecting the test album.
4. Whether the album advances through the tiles (shuffle) and at what interval.
5. Whether a **shared album** appears in the album picker.
6. Whether the tiles remain legible at the widget's actual pixel size on a
   phone, including under the widget's cropping and any text overlay it adds.
7. Any iOS-specific behaviour. The macOS widget is the closest available proxy
   and is not identical to iOS.

## Exact remaining test (iPhone, or Mac with manual clicks)

1. AirDrop or otherwise copy `production/exports/<piece>/widget/tiles/` to the
   device. Do not publish; keep the kit private.
2. Open Photos, import the tiles, create an album named `T07 test — <piece>`,
   add all tiles, and sync if needed.
3. Add the **Photos** widget (size 2×2 or wide) to the home screen / desktop.
4. Long-press the widget → Edit → Album → choose `T07 test — <piece>`.
5. Record:
   - whether the album appears in "My Albums",
   - whether a shared album (if one exists) appears in "My Albums" or
     "Smart Albums",
   - whether the widget renders a tile within 30 s,
   - whether it advances through the tiles,
   - the effective crop of each tile at the widget's rendered size,
   - any OS-added text, time, or date overlays.
6. Delete the test album and imported tiles when finished. Do not leave test
   material in the library.
7. Repeat with a shared album if step 5 shows one is selectable.

## Conclusion

The macOS static evidence proves an album picker exists and advertises user and
smart albums, but it does not prove a widget renders, shuffles, or accepts a
shared album. The kit therefore documents `may_publish: false` and keeps the
widget path as a private test surface until the physical-device step above is
recorded.
