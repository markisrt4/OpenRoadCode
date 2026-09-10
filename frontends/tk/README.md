# Tk Frontend Layer

`frontends/tk` contains OpenRoadCode presentation implemented with Tkinter. It is a toolkit layer, not an alias for `orcUi`.

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

Application-specific Tk composition belongs in an application-named package. The integrated OpenRoadCode cockpit shell lives in `orc_ui/`; its root window, HOME layout, context rail, navigation panel, power dialog, and other shell-specific presentation are intentionally not generic Tk components.

## Building another Tk application

A future Tk application should create its own package, for example:

```text
frontends/tk/
    new_ui/
        __init__.py
        new_ui_app.py
        ...application-specific layout...
```

That application can reuse feature widgets and screens from the sibling feature packages, controllers from `controllers/`, and semantic contracts from `ui/`. It should implement `TkScreenHostIf` when it wants to host reusable Tk screens.

Do not make reusable feature packages import `frontends.tk.orc_ui.OrcUiApp` or other `orc_ui` modules. If a reusable component needs another operation, prefer adding the narrowest appropriate contract rather than importing an application shell.

## Dependency direction

The intended direction is:

```text
ui contracts
    ↑
controllers / application services
    ↑
reusable frontends/tk feature components
    ↑
frontends/tk/<application-specific-ui>
    ↑
application composition root
```

The composition root may select a concrete Tk frontend. The reusable frontend packages should not know which application selected them.
