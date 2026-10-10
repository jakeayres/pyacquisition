# News and updates

When the window opens, and on the setup page (`pyacquisition new`), a card in the corner can tell you:

| Card | When | Shown |
|---|---|---|
| **Fix** | A serious bug affects the version you run. | Marked important, at each start, until you update or choose **Don't show again**. |
| **Update** | A newer version is out. It gives the commands to update, after stopping the experiment: uv's first, as [installing](../getting_started/installation.md) uses it, then pip's. | At each start, until you update or choose **Don't show again**. A newer version shows again. |
| **What's new** | You upgraded since the last run. It lists the [changelog](changelog.md)'s highlights of each version since then. | Once for each upgrade. |
| **From the maker** | News from PyAcquisition's maker, such as a new tutorial. | Once for each message, and never while a task is running. |

One card shows at a time, the most important first, and **N more** opens the rest. Closing a fix or an update hides it until the next start. Closing what's new or the maker's news, or choosing **Don't show again**, hides it for good on this PC. A new install shows no What's new: everything is new.

**What's new** in the [command palette](interface.md#the-command-palette) (++ctrl+k++, then type `whats new`) lists them all again, whenever you like. Links open in your browser, not in the window.

## What is fetched

What's new comes from the changelog inside the package, so it needs no network. The rest is fetched:

- **When** a page first asks for it in a run, in the background. The window opens as quickly with no network, and a fetch that fails is left until the next run.
- **At most once a day.** A fetch is kept for a day, however often you start an experiment.
- **From** PyPI, for the newest version (`https://pypi.org/pypi/pyacquisition/json`), and the maker's feed of fixes and news, which is kept in PyAcquisition's public repository (`news/feed.json`), so every message it has held can be read there.
- **With nothing about you.** Each is a plain request, with no identifiers: which messages are for your version is worked out on your PC. The servers see only an address and a time, as for any web page.
- **Never** in an app built with [`pyacquisition build`](command_line.md), which shows only what's new from the changelog it was built with, and never from a script or an experiment with no page open.

A message is text, a link and at most one image. The page draws it, so a message can't run code in the window. Images are fetched by the experiment, kept on your PC, and only PNG and JPEG images of up to 1 MB are taken.

## Where it keeps what you have seen

In one file, `news.json`, with the images beside it in `news-images`:

| On | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\pyacquisition` |
| Elsewhere | `$XDG_DATA_HOME/pyacquisition`, or `~/.local/share/pyacquisition` |

It holds the last version you ran, the messages you have closed, your choice about the maker's news, and the last fetch. Deleting it does no harm: the next run starts it again, as for a new install.

## Turning it off

- **News from the maker:** **Don't show news from the maker** under one of its cards, or the box in **What's new**. Fixes, updates and what's new still show.
- **For a whole PC**, set the environment variable `PYACQUISITION_NEWS`:

| `PYACQUISITION_NEWS` | Does |
|---|---|
| `all` | Everything above. The default. |
| `updates` | Fixes, updates and what's new, and no news from the maker. |
| `off` | Nothing is fetched, and no card is shown. **What's new** in the palette still lists the changelog. |

Two more variables are for those who look after PCs, and for previewing:

| Variable | Does |
|---|---|
| `PYACQUISITION_NEWS_DIR` | The folder for `news.json`, in place of the one above. |
| `PYACQUISITION_NEWS_FEED` | A feed's address, or a file, read in place of the maker's, and every run. To see how a message will look before it is published. |

## The feed

The maker's feed is a JSON file:

```json
{
  "messages": [
    {
      "id": "nested-sweep-tutorial",
      "kind": "news",
      "title": "New tutorial: a sweep inside a sweep",
      "text": "Step a field at each temperature, and watch the map fill in. [Read it](https://...)",
      "image": {"url": "https://.../map.png", "alt": "A map from a nested sweep"},
      "link": {"label": "Read more", "url": "https://..."},
      "until": "2027-01-31"
    }
  ]
}
```

| Key | Is |
|---|---|
| `id` | Letters, digits, `.`, `_` and `-`, never used for another message. Required. |
| `kind` | `fix` or `news`. Required. |
| `title`, `text` | Plain text. In `text`, a blank line starts a paragraph, lines starting `- ` are a list, and `[label](https://...)` is a link. Required. |
| `versions` | The versions it is for, such as `<0.4.1` or `>=0.3.0,<0.3.3`. All of them if left out. |
| `from`, `until` | The first and last day to show it, such as `2027-01-31`. |
| `link` | A button: `{"label": ..., "url": "https://..."}`. |
| `image` | `{"url": "https://...", "alt": ...}`. In a feed in a file, `url` can be a file beside it. |

An entry that breaks these rules is skipped, and the rest are shown.
