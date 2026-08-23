# Music-Reactive Lighting

`controllers/music_lighting` converts frontend-neutral music analysis into
hardware-neutral RGB and brightness frames. The visualizer and lighting do
not call one another directly; they consume the same analysis stream.

```text
PipeWire PCM
  -> MusicAnalyzer
  -> MusicAnalysisPresenter
       +-> visualizer frontend
       +-> MusicLightingController
             -> selected pattern
             -> brightness limit
             -> MusicLightingOutputAdapter
             -> LightingControllerIf
             -> BLE lighting hardware
```

Available patterns include spectrum flow, beat pulse, percussion, color wave,
and ambient. The output adapter coalesces rapid analysis frames and limits
hardware traffic to ten updates per second by default. It also suppresses
small color and brightness changes, which protects slower BLE controllers
from an unbounded command queue.

The Car UI visualizer provides quick enable, pattern, and intensity controls.
The shared lighting screen remains the destination for device connection and
manual lighting configuration. Current reactive output is one global RGB
color and brightness value; it does not address independent LED pixels or
zones.
