import { executeDrawing } from "./code-language.js";

self.addEventListener("message", (event) => {
  try {
    const result = executeDrawing(event.data.source);
    self.postMessage({ type: "result", ...result });
  } catch (error) {
    self.postMessage({
      type: "error", message: error instanceof Error ? error.message : "Drawing failed.",
      line: error.line, column: error.column,
    });
  }
});
