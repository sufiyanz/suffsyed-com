import "./home.js";
import "./questions.js";
import "./reader.js";
import "./archive.js";

document.body.classList.add("js");

const dialog = document.getElementById("artwork-dialog");
const image = document.getElementById("artwork-image");
const caption = document.getElementById("artwork-caption");
const original = document.getElementById("artwork-original");
const previous = document.getElementById("artwork-prev");
const next = document.getElementById("artwork-next");
const gallery = [...document.querySelectorAll("[data-gallery]")];
let active = null;

function showImage(link) {
  active = link;
  image.src = link.href;
  image.alt = link.querySelector("img")?.alt || link.dataset.caption || "Original artwork";
  caption.textContent = link.dataset.caption || image.alt;
  original.href = link.href;
  const index = gallery.indexOf(link);
  previous.hidden = next.hidden = index < 0;
  previous.disabled = index <= 0;
  next.disabled = index >= gallery.length - 1;
  document.getElementById("artwork-title").textContent = index >= 0 ? `Light(works) / Plate ${String(index + 1).padStart(2, "0")}` : "A closer look.";
}
document.addEventListener("click", event => {
  const link = event.target.closest("a[data-artwork]");
  if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  showImage(link);
  dialog.showModal();
});
document.querySelector("[data-close-dialog]").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", event => {
  if (event.target === dialog) {
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  }
});
previous.addEventListener("click", () => {
  const index = gallery.indexOf(active);
  if (index > 0) showImage(gallery[index - 1]);
});
next.addEventListener("click", () => {
  const index = gallery.indexOf(active);
  if (index >= 0 && index < gallery.length - 1) showImage(gallery[index + 1]);
});
dialog.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft" && !previous.hidden && !previous.disabled) previous.click();
  if (event.key === "ArrowRight" && !next.hidden && !next.disabled) next.click();
});
dialog.addEventListener("close", () => active?.focus());
