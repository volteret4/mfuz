"""
ThreadPoolExecutor-based parallel enrichment with checkpoint/resume.

Works with synchronous API libraries (spotipy, musicbrainzngs, etc.) because
it uses threads, not asyncio coroutines.

Usage:
    enricher = ConcurrentEnricher(
        workers=4,
        checkpoint_path="db/.cache/artist_checkpoint.sqlite",
    )

    def enrich_artist(artist_tuple):
        artist_id, artist_name = artist_tuple
        return {
            "id": artist_id,
            "spotify": get_spotify_url(artist_name),  # calls RateLimiter internally
            "youtube": get_youtube_url(artist_name),
        }

    results = enricher.enrich(
        artists,           # list of (id, name) tuples
        enrich_artist,
        id_fn=lambda a: str(a[0]),  # unique ID for checkpoint
    )

    # results → list of (item, result_dict) for non-None results
    for item, data in results:
        cursor.execute("UPDATE artists SET spotify_url=? WHERE id=?",
                       (data["spotify"], data["id"]))
    conn.commit()
"""

import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from tqdm import tqdm as _tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


class ConcurrentEnricher:
    """
    Parallel item processor with optional checkpoint/resume.

    Thread safety: enrich_fn must be thread-safe (use locks for shared API clients).
    Already-processed items (from a previous interrupted run) are skipped when
    checkpoint_path is provided.
    """

    def __init__(
        self,
        workers: int = 4,
        checkpoint_path: Optional[str | Path] = None,
        checkpoint_table: str = "enricher_done",
    ):
        self.workers = workers
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.checkpoint_table = checkpoint_table
        self._done_ids: set[str] = set()

        if self.checkpoint_path:
            self._init_checkpoint()

    # ------------------------------------------------------------------
    # Checkpoint helpers

    def _init_checkpoint(self) -> None:
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self.checkpoint_path)) as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {self.checkpoint_table} "
                f"(item_id TEXT PRIMARY KEY, ts REAL)"
            )
            rows = conn.execute(
                f"SELECT item_id FROM {self.checkpoint_table}"
            ).fetchall()
        self._done_ids = {r[0] for r in rows}
        if self._done_ids:
            logger.info(
                "Checkpoint: skipping %d already-processed items",
                len(self._done_ids),
            )

    def _mark_done(self, item_id: str) -> None:
        if self.checkpoint_path:
            with sqlite3.connect(str(self.checkpoint_path)) as conn:
                conn.execute(
                    f"INSERT OR IGNORE INTO {self.checkpoint_table} "
                    f"(item_id, ts) VALUES (?,?)",
                    (item_id, time.time()),
                )

    def reset_checkpoint(self) -> None:
        """Clear the checkpoint so all items are processed again."""
        if self.checkpoint_path and self.checkpoint_path.exists():
            with sqlite3.connect(str(self.checkpoint_path)) as conn:
                conn.execute(f"DELETE FROM {self.checkpoint_table}")
            self._done_ids.clear()

    # ------------------------------------------------------------------
    # Main entry point

    def enrich(
        self,
        items: Iterable[Any],
        enrich_fn: Callable[[Any], Any],
        id_fn: Optional[Callable[[Any], str]] = None,
        desc: str = "Processing",
    ) -> List[Tuple[Any, Any]]:
        """
        Process each item with enrich_fn in parallel.

        Args:
            items:      Iterable of items to process.
            enrich_fn:  Callable(item) → result. Must be thread-safe.
                        Returning None marks the item as failed (not checkpointed).
            id_fn:      Optional callable(item) → str for checkpoint keys.
                        Defaults to str(item).
            desc:       Label for the tqdm progress bar.

        Returns:
            List of (item, result) tuples where result is not None,
            in completion order.
        """
        id_fn = id_fn or str
        all_items = list(items)

        pending = [it for it in all_items if str(id_fn(it)) not in self._done_ids]
        n_skipped = len(all_items) - len(pending)
        if n_skipped:
            logger.info("Skipping %d checkpointed items", n_skipped)

        results: List[Tuple[Any, Any]] = []
        progress = (
            _tqdm(total=len(pending), desc=desc, unit="item")
            if _HAS_TQDM
            else None
        )

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_map = {
                executor.submit(enrich_fn, item): item for item in pending
            }

            for future in as_completed(future_map):
                item = future_map[future]
                item_id = str(id_fn(item))
                try:
                    result = future.result()
                    if result is not None:
                        results.append((item, result))
                        self._mark_done(item_id)
                    else:
                        logger.warning("enrich_fn returned None for %s", item_id)
                except Exception as exc:
                    logger.error("Error processing %s: %s", item_id, exc)
                finally:
                    if progress:
                        progress.update(1)

        if progress:
            progress.close()

        logger.info(
            "Enrichment done: %d/%d successful", len(results), len(pending)
        )
        return results
