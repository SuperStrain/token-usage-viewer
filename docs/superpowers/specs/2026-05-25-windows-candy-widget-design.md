# Windows Candy Widget - Design

## Overview

Build a Windows-native desktop widget for `token-usage-viewer`.

The existing Textual TUI stays available. The new UI is a small floating desktop
window for quick token monitoring. It uses a bright candy-sticker visual style:
soft pastel gradient, rounded shapes, friendly status bars, and gentle alerts.

The widget should feel like a cute desktop status sticker rather than a full
dashboard. It is optimized for glanceability and low interruption.

Reference mockup:
`docs/superpowers/mockups/windows-widget-style-options.html`, option A.

## Goals

- Add a Windows-native floating widget entry point.
- Reuse the existing config loader, adapters, and data models.
- Keep the current TUI behavior and command unchanged.
- Support manual refresh and automatic refresh.
- Use the existing Windows config path behavior:
  `%APPDATA%\token-usage\config.yaml`.
- Allow an explicit config path with `--config`.
- Provide a path toward a future `token-usage-widget.exe` build.

## Non-Goals

- Do not replace the Textual TUI.
- Do not redesign platform adapters.
- Do not add account configuration editing inside the first widget version.
- Do not implement system tray behavior in the first version.
- Do not persist window position in the first version unless it falls out
  naturally from the chosen toolkit with minimal code.

## Recommended Approach

Use PySide6 / Qt for the Windows widget.

Reasons:

- Qt supports frameless windows, transparency, rounded corners, drag-to-move,
  timers, and polished native desktop behavior.
- The candy-sticker style needs better styling control than Tkinter can offer.
- It is less complex than using a WebView while still giving enough visual
  freedom.

## User Experience

### Window Form

- Default size: about `360 x 460`.
- Frameless floating window.
- Rounded outer container.
- Soft pastel background using a light yellow, blue, and pink gradient.
- Gentle drop shadow when the platform supports it.
- The window can be dragged by holding the header or empty background area.

### Header

Header content:

- App name: `Token Buddy`.
- Small status text:
  - `Refreshing...` while fetching.
  - `Updated HH:MM:SS` after a successful refresh.
  - `Some services need attention` when any card has an error or high usage.
- Small icon-style buttons:
  - Refresh.
  - Minimize.
  - Close.

### Platform Rows

Show four compact platform rows in the existing adapter order:

1. OpenCode Go
2. OpenAI
3. DeepSeek
4. ZhipuAI

Each row uses a white translucent rounded card.

For quota platforms:

- Platform name.
- Main value, usually highest quota percentage.
- A rounded progress bar.
- Secondary detail such as reset time or quota label.

For balance platforms:

- Platform name.
- Balance or monthly consumption.
- A small `OK` badge if no quota percentage is available.

Status handling:

- `ok`: pastel accent and normal text.
- `unconfigured`: muted state with `Not configured`.
- `error`: pink/red accent with a short error message.
- usage over 80%: warmer accent and included in the alert strip.

### Footer Alert Strip

The footer displays one short, friendly message:

- Empty or calm message if everything is normal.
- A high-usage warning if any quota exceeds 80%.
- A configuration hint if all platforms are unconfigured.
- A network/API hint if all configured platforms fail.

The copy should be brief and practical.

## Architecture

Add a new `token_usage.gui` package:

```text
src/token_usage/gui/
├── __init__.py
├── widget_app.py
├── worker.py
└── styles.py
```

### `widget_app.py`

Responsibilities:

- Own the `QApplication`.
- Parse CLI options for the widget entry point.
- Create and show the main widget window.
- Render the platform cards.
- Handle window dragging, refresh button, minimize, and close.

### `worker.py`

Responsibilities:

- Fetch usage data without blocking the UI thread.
- Reuse `create_adapters(config)` and each adapter's `fetch_usage()`.
- Return `list[PlatformUsage]` or per-platform errors through Qt signals.

The first version can use a `QThread` running `asyncio.run(...)` for each
refresh. This keeps the implementation simple and avoids mixing Qt and asyncio
event loops in the main thread.

### `styles.py`

Responsibilities:

- Store QSS strings and color constants for the candy-sticker theme.
- Keep visual styling out of business logic.

## Data Flow

1. `token-usage-widget` starts.
2. CLI parses `--config`, `--interval`, and `--no-auto-refresh`.
3. `load_config(config_path)` loads YAML and environment overrides.
4. `create_adapters(config)` creates platform adapters.
5. The widget starts a refresh worker.
6. Worker fetches all adapters concurrently.
7. UI receives `PlatformUsage` objects and updates rows.
8. A `QTimer` schedules the next refresh using `refresh_interval` from config
   or CLI.

## CLI

Add a new script entry point:

```toml
token-usage-widget = "token_usage.gui.widget_app:main"
```

Supported options:

- `--config PATH`: explicit config file.
- `--interval SECONDS`: auto refresh interval, defaulting to config
  `refresh_interval` or `300`.
- `--no-auto-refresh`: start with manual refresh only.

The existing `token-usage` TUI command remains unchanged.

## Dependencies

Add `PySide6` as a project dependency.

This increases install and build size, but it is appropriate for a native
Windows GUI. Packaging notes should mention that the GUI binary will be larger
than the TUI binary.

## Error Handling

- Adapter exceptions should not crash the widget.
- A failed platform row shows an error state with a short message.
- If every configured platform fails, footer copy should suggest checking
  network/proxy/token validity.
- If a platform is unconfigured, show a muted row instead of an exception.

## Testing

Unit tests should cover:

- Widget CLI argument parsing if factored into a pure helper.
- Mapping `PlatformUsage` objects into display view models.
- Alert footer message selection.
- Worker result handling with fake adapters or a pure fetch helper.

GUI rendering can be kept lightly tested because PySide6 visual tests are more
fragile in headless CI. Favor pure transformation helpers for deterministic
coverage.

Manual verification:

- Launch `token-usage-widget --config <path>`.
- Confirm window appears as a small frameless candy-sticker widget.
- Confirm drag-to-move works.
- Confirm refresh button updates status.
- Confirm unconfigured, error, normal, and high-usage states render clearly.

## Documentation Updates

Update README and AGENTS after implementation:

- Add `token-usage-widget` run command.
- Add Windows widget config path notes.
- Add widget build command.
- Mention Windows Terminal/PowerShell for TUI, and native window for widget.

## Open Implementation Notes

- Prefer simple text glyphs or Qt-drawn shapes for the first mascot/accent.
- Avoid image assets in the first version unless packaging remains simple.
- Keep labels short so the widget stays compact.
- Keep the TUI and GUI modules independent except for shared config, adapters,
  and models.
