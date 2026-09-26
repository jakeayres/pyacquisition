# Vendored libraries

Served as they are, with no build step. Each folder holds the library's licence.

| Library | Version | Files | Source |
|---|---|---|---|
| Preact | 10.29.8 | `preact/preact.module.js`, `preact/hooks.module.js` | npm `preact`: `dist/preact.module.js`, `hooks/dist/hooks.module.js` |
| htm | 3.1.1 | `htm/htm.module.js` | npm `htm`: `dist/htm.module.js` |
| uPlot | 1.6.32 | `uplot/uPlot.esm.js`, `uplot/uPlot.min.css` | npm `uplot`: `dist/uPlot.esm.js`, `dist/uPlot.min.css` |

The `sourceMappingURL` comments were removed, since the maps are not shipped.
To update, download the package tarball from the npm registry, copy the same
files over, and update this table.
