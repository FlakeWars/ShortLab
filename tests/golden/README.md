# Golden tests (renderer)

Golden tests porównują:
- hash metadanych (`metadata.json`)
- hash pierwszej, środkowej i ostatniej klatki PNG

Dlaczego nie hash całego wideo?
- kompresja wideo może się różnić między wersjami FFmpeg, mimo identycznych klatek.

Regeneracja goldenów:
- `make golden`
