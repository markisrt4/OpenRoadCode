# Text input foundation

Text entry is separate from physical-key mapping in `input_events` and
`controllers/input/input_manager.py`. Native fields and browser fields own their
text. The shared controller never reads, copies, logs, or stores typed contents.

## Contracts and ownership

- `ui/input/text_input_request_handler_if.py`: begin a session, show/hide its
  keyboard, submit, or cancel. Every request after begin carries its session token.
- `ui/input/text_input_target_if.py`: the supplied native/browser adapter focuses,
  submits, or cancels its field. Cancel behavior is specific to that field.
- `ui/input/text_input_ui_if.py`: immutable presentation state and an optional
  observer contract. `keyboard_requested` records the controller's request, not
  a guarantee that an external window is mapped or that its process remains alive.
- `hardware_io/keyboard/soft_keyboard_if.py`: platform keyboard availability,
  show/hide, and cleanup. It is independent of Tk, Chromium, and key readers.
- `controllers/input/text_input_controller.py`: owns the active session, focus
  requests, stale-token rejection, error state, and keyboard lifecycle.

Composition constructs the keyboard adapter, injects it into the controller,
binds an optional view with `set_ui`, and supplies field adapters at session
begin. Requests and presentation callbacks run synchronously on the frontend
thread. There are no background completions in this first version.

Begin focuses a field without opening the keyboard automatically. Showing the
keyboard then requests focus on the same field again. Hiding the keyboard keeps
the session active, so a physical keyboard can still be used. Switching fields
retires the previous token without submitting, cancelling, or erasing that field.
Old tokens cannot affect the replacement session. Successful submit/cancel
retires the session even if subsequent keyboard cleanup fails, avoiding duplicate
submission; beginning another session or closing the controller retries cleanup.

Close the controller before destroying field adapters. Close releases the
keyboard without calling potentially destroyed field callbacks; repeated close
is inert. Errors are exposed as generic state messages without including field
contents. Target submit/cancel callbacks may synchronously begin another session;
completion of the previous request must not close that replacement session.

## Existing system keyboards

`hardware_io/keyboard/process_soft_keyboard.py` is an optional process adapter
for an explicitly configured **foreground, non-focus-stealing** keyboard command.
It checks executable availability, launches argument arrays without a shell,
inherits the environment (with an optional display override), and terminates and
reaps only its own child. It never installs a keyboard, selects one automatically,
or terminates a desktop-managed keyboard by process name. Shutdown waits are
bounded; a keyboard ignoring termination is killed and reaped.

A command that daemonizes or controls a separately managed keyboard needs a
backend-specific adapter implementing `SoftKeyboardIf`. This process adapter
cannot guarantee focus behavior for an arbitrary executable; that must be checked
with the chosen system keyboard. UI toolkit focus operations belong in field
adapters, not in widgets calling controllers or platform tools directly.

No new dependency, system keyboard selection, browser/Tk field adapter, UI button,
or application-composition wiring is included yet. The available Pi and
Termux:X11 keyboards and their focus behavior still need device verification
before selecting and wiring a production backend. Android's input method and a
Linux keyboard inside Termux:X11 are distinct mechanisms; neither is presumed
available just because the other exists.

## Validation

From the repository checkout with its Python environment active:

```bash
git switch feature/waze-live-map
python -m pytest controllers/input/unit_test/test_text_input_controller.py hardware_io/keyboard/unit_test/test_process_soft_keyboard.py -q
python scripts/check_ui_boundaries.py
```

The tests exercise ownership, stale requests, reentrant completion, failure
recovery, unavailable keyboards, and owned-process cleanup without launching a
real keyboard. Device focus and browser typing remain pending integration; the
full quality gate remains for the user to run before merge.
