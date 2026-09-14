# Streaming Radio

This package owns the application-facing internet-radio behavior for OpenRoadCode.

The radio UI should not know which public directory discovered a station or which
local media engine decodes its stream. `StreamingRadioController` sits between
those concerns.

## Flow

<aside class="orc-diagram-legend" aria-label="Architecture diagram legend">
  <strong>Diagram key</strong>
  <span><i class="orc-legend-swatch orc-legend-app"></i>App / UI</span>
  <span><i class="orc-legend-swatch orc-legend-service"></i>Service / runtime</span>
  <span><i class="orc-legend-swatch orc-legend-controller"></i>Controller / domain</span>
  <span><i class="orc-legend-swatch orc-legend-message"></i>Messaging / contract</span>
  <span><i class="orc-legend-swatch orc-legend-adapter"></i>Protocol / hardware</span>
  <span><i class="orc-legend-swatch orc-legend-external"></i>External / input</span>
</aside>

```mermaid
flowchart TD
    provider["Station directory / provider"] --> providerIf["StreamingStationProviderIf"]
    providerIf --> controller["StreamingRadioController"]
    controller --> artwork["Artwork cache"]
    controller --> player["StreamingAudioPlayerIf"] --> audio["System audio"]

    classDef orcApp fill:#dbeafe,stroke:#2563eb,color:#172554;
    classDef orcService fill:#ede9fe,stroke:#7c3aed,color:#2e1065;
    classDef orcController fill:#dcfce7,stroke:#16a34a,color:#14532d;
    classDef orcMessage fill:#ffedd5,stroke:#ea580c,color:#7c2d12;
    classDef orcAdapter fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
    classDef orcExternal fill:#f3f4f6,stroke:#6b7280,color:#1f2937;
    class provider,audio orcExternal;
    class providerIf,player orcMessage;
    class controller,artwork orcController;
```

`StreamingStation` is the provider-independent station record used by frontends.
Artwork is cached below the XDG cache root at
`openroadcode/streaming_radio/images` so a station grid does not repeatedly fetch
logos while driving.

The first provider implementation is expected to use an internet radio directory
for regional discovery. Provider-specific HTTP and JSON belong under `protocols/`,
not in this controller package.

The first orcUi radio screen presents two launch choices: RF Radio and Streaming
Radio. RF owns SDR++/Rigctl/telemetry. Streaming Radio owns internet discovery,
station artwork, and stream playback. Shared station/favorite concepts can be
introduced above these two transports later without coupling them now.
