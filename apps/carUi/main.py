"""Executable entry point for the Car UI application."""

from __future__ import annotations

from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.car_ui_frontend import CarUiFrontend
from apps.carUi.car_ui_startup import initialize_car_ui_dependencies
from frontends.tk.runtime import configure_display


def main() -> None:
    try:
        configure_display()
    except RuntimeError as exc:
        raise SystemExit(f"[CarUI] {exc}") from exc

    app: CarUiFrontend | None = None
    dependencies: CarUiDependencies | None = None
    try:
        dependencies = initialize_car_ui_dependencies()
        app = CarUiFrontend(dependencies)
        if not app.initialize():
            raise RuntimeError("Car UI frontend failed to initialize")
        app.run()
    except KeyboardInterrupt:
        print("\n[CarUI] Stopped")
    finally:
        try:
            if app is not None:
                app.shutdown()
        finally:
            if dependencies is not None:
                dependencies.close()


if __name__ == "__main__":
    main()
