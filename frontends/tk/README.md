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


## orcUi cockpit shell

The integrated cockpit UI is owned by `apps/orcUi/frontend/tk`. The shell is deliberately decomposed instead of concentrating presentation in `OrcUiApp`:

- `shell_view.py`, `shell_chrome.py`, and `shell_content.py` own shell layout and chrome.
- `side_nav.py` and `bottom_bar.py` own the persistent driver controls.
- The footer carries subtle shell-owned breadcrumbs alongside service status, so feature panels do not spend vertical space repeating their location.
- `screen_builders.py` assembles application-owned screens.
- `presentation_state.py` keeps shell presentation state separate from widget construction.
- Vehicle views are split into dedicated Performance, Health, ECU, Off-Road, and Trip panels.

The target cockpit canvas is 1280x720, while the same shell must remain usable in the smaller effective viewport presented by Termux/X11. Persistent navigation and bottom controls therefore use shared metrics rather than screen-specific hard-coded sizing. New panels should fit inside the existing shell allocation rather than increasing the minimum window size. Breadcrumbs are derived from primary navigation plus the active screen/subview (for example `VEHICLE › ECU` or `MEDIA › SPOTIFY`) and belong to the shell rather than individual panel headers.

### Vehicle presentation

The vehicle area separates information by driver intent:

- **Performance** presents live driving gauges and immediately useful vehicle state.
- **Health** presents temperatures and vehicle/engine health information.
- **ECU** interprets fuel control, mixture, engine load, and ignition behavior.
- **Off-Road** presents heading, roll, pitch, grade, altitude, and related navigation state.
- **Trip** presents accumulated trip and economy information.

ECU cards use restrained semantic accents to distinguish domains without turning the cockpit into a collection of unrelated themes. Fuel control uses amber, mixture uses ORC blue, engine load uses orange, and ignition uses green. Card surfaces and borders remain neutral so telemetry retains visual priority.

### Quality gate

`scripts/quality_gate.py` is the branch-level UI quality entry point. The ORC UI also enforces a Python module-size limit through `scripts/check_python_module_size.py`; large shell or feature modules should be decomposed rather than extending the limit. Run the quality gate and ORC UI tests before merging substantial shell changes.
