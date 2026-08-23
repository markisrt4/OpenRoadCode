# Song Recognition Controller

`controllers/song_recognition` identifies recent audio without coupling a
provider to Car UI or Web UI. `SongRecognitionController` owns request
serialization, clip validation, diagnostic logging, metadata enrichment, and
persistent metadata caching. `SongRecognitionIf` is the provider boundary;
`AcrCloudSongRecognizer` is the current implementation.

## Runtime flow

```text
PipeWire monitor
  -> PcmMusicAnalysisSource (fresh, non-overlapping PCM buffer)
  -> 10-second mono 16-bit WAV
  -> SongRecognitionController
  -> AcrCloudSongRecognizer
  -> normalized SongRecognitionResult
  -> cached metadata / optional Spotify enrichment
  -> MusicVisualizerUiIf
```

FFT analysis windows overlap for smooth visualization. `AudioFrame` reports
`new_sample_count` so the recognition buffer stores only newly captured PCM;
reusing the complete analysis window would duplicate audio and invalidate an
acoustic fingerprint.

Recognition remains disabled until ten seconds of current-session audio are
buffered. The exact submitted clip is written to
`/tmp/openroadcode-recognition-last.wav` for diagnostics and is replaced by
the next attempt.

## ACRCloud configuration

Create an ACRCloud Audio & Video Recognition project using line-in audio and
the Audio Fingerprinting engine. Enable the ACRCloud Music bucket and Spotify
third-party metadata if Spotify artwork and playback handoff are wanted.

Configure credentials interactively from the repository root:

```bash
scripts/setup_acrcloud_credentials.py
```

The script atomically updates:

```text
~/.config/openroadcode/secrets.env
```

with file mode `0600`. The supported keys are:

```text
ACRCLOUD_HOST=identify-us-west-2.acrcloud.com
ACRCLOUD_ACCESS_KEY=...
ACRCLOUD_ACCESS_SECRET=...
```

Process environment variables override the user file. The legacy
`/etc/openroadcode/secrets.env` file remains a lower-priority fallback.

## Metadata cache

Normalized results are stored in
`~/.cache/openroadcode/song_recognition` under every available stable ID:

- ISRC
- ACRCloud recording ID
- Spotify track ID

After ACRCloud recognizes a song, these IDs are used to reuse cached artwork
and enriched Spotify metadata. This avoids a repeat Spotify catalog request,
but it does **not** avoid the ACRCloud request: none of those IDs are known
before recognition. A future local acoustic-fingerprint namespace (for
example Chromaprint) is required for offline or provider-free repeat lookup.

Cache files contain metadata and URLs, not recorded audio. They may be removed
safely; subsequent recognition reconstructs them.

## Spotify enrichment

When ACRCloud returns a Spotify track ID and Spotify is authenticated, the
controller retrieves the canonical URI, service URL, and album artwork from
Spotify. Car UI displays the artwork and offers **Play in Spotify**, which
starts the recognized track on the active Spotify device and opens the
existing Spotify panel. Playback requires an account/device supported by the
Spotify playback API.
