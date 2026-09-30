/* Numbered pins in code: a comment that is only a number in brackets, such as
   `# (1)`, becomes an orange pin like those on a tutorial's "What you built", keyed
   to the numbered notes under the block (a .gs-legend.pa-notes). Without this script
   the comments read as they are written, and still match the notes.

   The pin's number is drawn by the stylesheet (reference.css), so copying the code
   copies no stray digits. */
(() => {
  "use strict";

  const PIN = /^\s*(?:#|\/\/)\s*\((\d+)\)\s*$/;

  function pin(root) {
    for (const comment of root.querySelectorAll(".highlight code .c, .highlight code .c1, .highlight code .ch")) {
      const match = PIN.exec(comment.textContent);
      if (!match) continue;
      const marker = document.createElement("span");
      marker.className = "pa-pin";
      marker.dataset.n = match[1];
      marker.setAttribute("aria-label", `note ${match[1]}`);
      comment.replaceWith(marker);
    }
  }

  function init() {
    pin(document);
  }

  if (window.document$ && typeof window.document$.subscribe === "function") window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
