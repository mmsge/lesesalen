"""Lesesalen — a Mastodon client that shows you only the book posts.

The server exists for exactly one reason: BookWyrm instances do not send CORS
headers for ActivityPub fetches, so the browser cannot re-fetch the origin object
of a post to recover the rating, review title, quoted passage and book link that
Mastodon threw away. Everything else — OAuth, the timeline, replies, favourites —
happens in the browser against the reader's own instance.

Consequently there is no user table, no token storage, no follow graph and no
reading history anywhere in this package. Keep it that way.
"""

__version__ = "1.0.0"
