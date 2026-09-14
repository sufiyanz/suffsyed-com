const profiles = {
  "scratch-terminal": { alphabet: "{}[]<>:=01af/+", cell: [1, 1.45], size: 1.3, jitter: 0, weight: 500, reveal: "scan", angle: 0, underlay: .12 },
  "ink-studio": { alphabet: ".,:'`·", cell: [.7, .95], size: 1.05, jitter: .36, weight: 400, reveal: "grain", angle: -.035, underlay: .26 },
  "pocket-darkroom": { alphabet: "oO0·:.", cell: [.95, 1.1], size: 1.45, jitter: .08, weight: 500, reveal: "exposure", angle: .025, underlay: .1 },
  "blackout-poetry": { alphabet: "", cell: [3.4, 1.45], size: 1.5, jitter: .15, weight: 600, reveal: "pieces", angle: -.05, underlay: .16, serif: true },
  "agent-terrarium": { alphabet: "·.:+'", cell: [.75, 1.3], size: 1.2, jitter: .25, weight: 500, reveal: "trails", angle: .025, underlay: .12 },
  "signal-noise": { alphabet: "#_:=[]", cell: [1.6, 1.5], size: 1.75, jitter: 0, weight: 700, reveal: "blocks", angle: 0, underlay: .08 },
  "sound-loom": { alphabet: "|:!.-", cell: [.75, 2.15], size: 1.8, jitter: 0, weight: 500, reveal: "columns", angle: -.02, underlay: .16 },
  "assumption-lab": { alphabet: "0123456789+×.", cell: [1.25, 1.75], size: 1.3, jitter: 0, weight: 400, reveal: "coordinates", angle: .035, underlay: .1 },
  "generative-postcard": { alphabet: "POST:/+—", cell: [1.65, 1.25], size: 1.5, jitter: .12, weight: 600, reveal: "stamp", angle: -.085, underlay: .18 },
};

export function profileFor(id, data, seed) {
  const profile = profiles[id];
  if (!profile) throw new Error(`No signature scene profile for ${id}.`);
  const words = profile.serif
    ? (data.passages[seed % data.passages.length].text.match(/\p{L}+/gu) || []).slice(0, 80)
    : [...profile.alphabet];
  if (!words.length) throw new Error("The signature scene has no original passage words.");
  return { ...profile, glyphs: words.map(word => word.slice(0, 5)) };
}
