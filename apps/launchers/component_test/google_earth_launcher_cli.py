from apps.launchers.google_earth_launcher import GoogleEarthLauncher


def main() -> None:
    earth = GoogleEarthLauncher()

    earth.set_location(
        latitude=42.3314,
        longitude=-83.0458,
    )

    earth.launch(":0")


if __name__ == "__main__":
    main()
