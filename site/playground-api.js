/**
 * Cover playground contract v1. Documentation only: modules need not import this file.
 * mount(root, context) builds a meaningful static view and returns an initially inactive controller.
 * Only mutate root. Signal abort and destroy must stop resources, even during pending initialization.
 * All state is ephemeral. Use textContent for user text, same-origin assets, and explicit downloads.
 * reportError during mounting fails initialization; once ready it reports an action error without
 * discarding work. Modules stop any failed work themselves; thrown lifecycle errors remain fatal.
 *
 * @typedef {{reducedMotion: boolean, forcedColors: boolean}} Preferences
 * @typedef {{width: number, height: number, dpr: number}} Dimensions
 * @typedef {{id: string, src: string, alt: string, title: string, width: number, height: number}} Photo
 * @typedef {{id: string, text: string, title: string, href: string}} Passage
 * @typedef {{
 *   signal: AbortSignal,
 *   seed: number,
 *   random: () => number,
 *   preferences: Preferences,
 *   palette: {forest: string, green: string, stone: string, paper: string, white: string, ink: string},
 *   data: {signature: {src: string, viewBox: number[]}, photos: ReadonlyArray<Photo>, passages: ReadonlyArray<Passage>},
 *   setStatus: (message: string) => void,
 *   reportError: (message: string, error?: Error) => void
 * }} PlaygroundContext
 * @typedef {{
 *   setActive: (active: boolean) => void,
 *   resize: (dimensions: Dimensions) => void,
 *   setPreferences: (preferences: Preferences) => void,
 *   destroy: () => (void | Promise<void>)
 * }} PlaygroundController
 */
