# Persistent Cache Controller

`controllers/cache` provides toolkit- and domain-independent storage for
opaque cached bytes.

`PersistentCache` hashes logical keys into filenames and writes through a
temporary file followed by atomic replacement. It deliberately does not own
serialization, expiration, downloading, or domain validation.

```python
from controllers.cache import PersistentCache

cache = PersistentCache("~/.cache/openroadcode/example")
cache.put("latest", b"payload")
payload = cache.get("latest")
cache.remove("latest")
```

Domain controllers layer their own policy on top. `ImageCache` stores source
image bytes with an `.image` suffix, while `WeatherSnapshotCache` serializes a
typed forecast snapshot as JSON. `SongMetadataCache` stores normalized song
recognition results under ISRC and provider IDs. That metadata cache can avoid
repeat enrichment requests after recognition, but cannot replace recognition
until a local acoustic fingerprint supplies a lookup key.

Run its tests from the repository root:

```bash
venv/bin/python -m unittest discover \
  -s controllers/cache/unit_test -p 'test_*.py'
```
