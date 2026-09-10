# Tk Frontend Layer

`frontends/tk` contains reusable OpenRoadCode presentation implemented with Tkinter. It is a toolkit layer, not an application package and not an alias for `orcUi`.

## Package boundary

Reusable Tk components belong directly under feature-oriented packages such as:

- `automotive/`
- `media/`
- `radio/`
- `games/`
- `lighting/`
- `menu/`
- `system/`
- `theme/`
- `runtime/`

Reusable screens should depend on narrow Tk or toolkit-independent contracts rather than a concrete application shell. `TkScreenHostIf` is the host contract for reusable Tk screens.

Application-specific Tk presentation does **not** belong under `frontends/tk`. The integrated orcUi cockpit shell lives under `apps/orcUi/frontend/tk`; its root window, HOME layout, context rail, navigation panel, power dialog, and other shell-specific presentation are application-owned.

## Building another Tk application

A future Tk application should own its shell inside its own application package, for example:

```text
frontends/tk/
    automotive/
    media/
    radio/
    games/
    ...reusable Tk features...

apps/orcUi/frontend/tk/
    orc_ui_app.py
    ...orcUi-specific layout...

apps/diagnosticUi/frontend/tk/
    diagnostic_ui_app.py
    ...diagnostic-specific layout...
```

Each application can reuse feature widgets and screens from `frontends/tk`, controllers from `controllers/`, and semantic contracts from `ui/`. An application shell should implement `TkScreenHostIf` when it wants to host reusable Tk screens.

Do not make reusable `frontends/tk` packages import `apps.orcUi`, `OrcUiApp`, or any other application-specific frontend. If a reusable component needs another operation, prefer adding the narrowest appropriate contract rather than importing an application shell.

## Dependency direction

The intended direction is:

```text
ui contracts
    ↑
controllers / application services
    ↑
reusable frontends/tk feature components
    ↑
apps/<application>/frontend/tk
    ↑
application composition root
```

The application composition root may select Tk and assemble reusable Tk features into its concrete shell. The reusable frontend packages should not know which application selected them.
