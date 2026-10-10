# The news feed

`feed.json` is the feed of fixes and news that PyAcquisition's news card reads
(see `docs/reference/news.md`). Every message it has ever held is in this
file's history.

Before publishing a message, preview it: set `PYACQUISITION_NEWS_FEED` to a
copy of this file and start an experiment. Each message's `id` is kept for
ever, so a message closed on a PC is never shown there again.
