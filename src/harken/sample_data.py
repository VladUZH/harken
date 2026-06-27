"""Bundled sample dataset for the zero-config demo.

These are SYNTHETIC, illustrative mentions about a fictional product ("Quill", a
note-taking app) — not real people's posts. They exist so `harken demo` shows the
full pipeline (aggregation + sentiment + themes) instantly, with no network and no
keys. Real tracking uses live sources via `harken track`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from harken.models import Mention

DEMO_QUERY = "Quill"

# (source, author, title, text, score, days_ago)
_RAW = [
    ("hackernews", "swyx", "Show HN: Quill – a fast local-first note app", "", 412, 13),
    ("hackernews", "patio11", None, "Been using Quill for a month. The speed is genuinely impressive, opens instantly even with 5000 notes.", 88, 12),
    ("hackernews", "tptacek", None, "The pricing jumped to $12/mo which feels steep for a notes app. Otherwise solid.", 64, 12),
    ("hackernews", "rachelbythebay", None, "Quill's markdown export is broken for nested lists. Reported it twice, no response.", 41, 11),
    ("hackernews", "antirez", None, "I love that Quill stores everything as plain files. No lock-in, works with my git workflow.", 120, 10),
    ("hackernews", "jgrahamc", None, "The sync feature is unreliable — lost a note yesterday after a conflict. Scary for a notes app.", 73, 9),
    ("hackernews", "mitchellh", None, "Quill is the first notes app where search is actually fast. Sub-100ms across my whole vault.", 95, 8),
    ("reddit", "u/devnull42", "Quill vs Obsidian?", "Switched from Obsidian to Quill last week. The UI is so much cleaner and it's way less bloated.", 156, 9),
    ("reddit", "u/notes_nerd", "Quill pricing is too high", "$12/mo is ridiculous when Obsidian is free. The app is nice but not that nice.", 203, 7),
    ("reddit", "u/markdownfan", None, "Quill's keyboard shortcuts are fantastic. Feels like it was built by people who actually take notes.", 88, 7),
    ("reddit", "u/privacymatters", None, "Love that Quill is local-first and doesn't phone home. No telemetry, no account required to start.", 174, 6),
    ("reddit", "u/buggy_user", None, "Quill crashed three times today on a large vault. Performance falls apart past 10k notes.", 61, 6),
    ("reddit", "u/casualnoter", None, "Honestly Quill is just okay. Does the job but nothing groundbreaking. The docs are thin.", 19, 5),
    ("reddit", "u/teamlead99", None, "We rolled Quill out to the whole team. Setup was painful and the docs are missing half the features.", 44, 5),
    ("reddit", "u/openuser", None, "Wish Quill were open source. Great app but I don't trust a closed notes app with my second brain.", 210, 4),
    ("mastodon", "writer@mastodon.social", None, "Quill has become my daily driver for writing. The distraction-free mode is beautiful and fast.", 32, 8),
    ("mastodon", "dev@fosstodon.org", None, "Quill is closed source and that's a dealbreaker for me. Looking for an open alternative.", 47, 5),
    ("mastodon", "phd@scholar.social", None, "The pricing model killed it for me. $12/mo for notes I could keep in plain markdown? No thanks.", 28, 5),
    ("mastodon", "maker@mastodon.online", None, "Quill's plugin API is surprisingly good. Wrote a custom exporter in an afternoon.", 51, 3),
    ("mastodon", "student@mas.to", None, "Quill keeps crashing on my old laptop. Performance is rough on low-end hardware.", 15, 3),
    ("bluesky", "tess.bsky.social", None, "Quill is the best note app I've tried this year. Fast, clean, local-first. Highly recommend.", 64, 7),
    ("bluesky", "omar.bsky.social", None, "The Quill sync bug bit me again. Lost edits after switching devices. Be careful.", 38, 4),
    ("bluesky", "lena.bsky.social", None, "Quill's docs are seriously lacking. Spent an hour figuring out how templates work.", 22, 4),
    ("bluesky", "raj.bsky.social", None, "Quill's search is instant and the UI is gorgeous. Worth trying if you take a lot of notes.", 70, 3),
    ("bluesky", "mia.bsky.social", None, "Quill pricing went up again. Loved it at launch, but $12/mo is too much for me now.", 45, 2),
    ("hackernews", " ", None, "Quill is fast but the lack of mobile sync reliability makes it a non-starter for my workflow.", 33, 2),
    ("reddit", "u/longtimeuser", None, "Two years on Quill. Still the fastest, still local-first, still love it. The plugin ecosystem grew a lot.", 130, 2),
    ("reddit", "u/skeptic", None, "Quill is fine but overhyped. The search is good, the sync is bad, the price is worse.", 57, 1),
    ("mastodon", "artist@mastodon.art", None, "Quill's writing experience is genuinely delightful. Typography and speed are top notch.", 26, 1),
    ("bluesky", "kai.bsky.social", None, "Quill crashed and corrupted a note. Backups saved me but this shouldn't happen in a notes app.", 41, 1),
    ("hackernews", "newuser", None, "Quill's onboarding is confusing and the documentation doesn't cover sync setup at all.", 18, 1),
    ("reddit", "u/happycamper", None, "Quill made me actually enjoy taking notes again. Fast, beautiful, no bloat. Best purchase this year.", 99, 0),
]


def sample_mentions() -> list[Mention]:
    now = datetime.now(timezone.utc)
    out: list[Mention] = []
    for i, (source, author, title, text, score, days_ago) in enumerate(_RAW):
        out.append(
            Mention(
                source=source,
                query=DEMO_QUERY,
                author=author.strip() or None,
                title=title,
                text=text,
                url=f"https://example.invalid/{source}/{i}",
                created_at=now - timedelta(days=days_ago, hours=i % 24),
                score=score,
            )
        )
    return out
