# Cadence
For every music lover to play their offline beats












*About the files* -- 


audio_player.py: Implement core audio playback logic — encapsulates playback control (play/pause/stop/seek), manages playback state and current track metadata, interfaces with audio backend, and exposes events/callbacks for UI updates and progress tracking.

database.py: Add lightweight persistence layer — defines SQLite (or similar) schema and helper functions for storing playlists, track metadata, user settings, and playback history; includes migration helpers and safe query wrappers.

downloader.py: Add download manager — handles asynchronous downloading of tracks/lyrics/album art with progress reporting, retry/backoff logic, and safe file writes to temporary files before commit.

file_watcher.py: Implement filesystem watcher — monitors music library directories for adds/removals/changes and emits events to trigger rescans or UI refreshes; debounces rapid changes and handles nested directories.

music_scanner.py: Add music scanning utilities — scans directories for audio files, extracts metadata (tags, duration), detects duplicates, and builds/updates the in-app library index.

main.py: Application entrypoint — initializes configuration, logging, database, core services (player, scanner, updater), constructs the main UI window, and starts the application event loop.

download_dialog.py: Add download UI component — dialog for downloading tracks/lyrics/album art with progress bars, queue controls, and status messages.

icons.py: Provide icon registry/loader — centralized helper to load SVG/PNG icons for the UI, manage theme variants (light/dark), and cache loaded pixmaps.

lyrics_display_widget.py: Lyrics display component — widget to render synchronized or static lyrics, support scrolling, highlighting current line, and font/size settings.

main_window.py: Main window layout and wiring — top-level window composing player, playlist, search, and settings; handles window state persistence and global shortcuts.

player_widget.py: Player UI controls — play/pause, next/previous, seek bar, volume, shuffle/repeat buttons, and currently playing track display with album art.

playlist_widget.py: Playlist view and interactions — displays current playlist, supports reordering, item selection, context menu actions (remove, save, export), and drag-and-drop.

settings_dialog.py: Settings/preferences UI — dialog exposing configurable options (paths, audio backend, theme, scrobbling, auto-updates) with validation and apply/cancel semantics.

style.py: UI styling helpers — application-wide style constants, theme definitions, and utility functions to apply consistent spacing, fonts, and colors.

album_art.py: Album art utilities — fetches, caches, and serves album art images; includes resizing, placeholder handling, and cache eviction policy.

config.py: Configuration helper — loads and persists cadence_config.json, provides typed accessors, default values, and validation for required fields.

logger.py: Logging wrapper — configures app logging (file/console), log rotation, and helper functions for structured logs and exception reporting.

lyrics_fetcher.py: Lyrics retrieval utility — fetches lyrics from local files or remote services, supports synchronized LRC parsing, caching, and fallback strategies.

metadata_reader.py: Metadata extraction helper — reads ID3/metadata tags from audio files, normalizes fields (artist/title/album), and extracts embedded images.

paths.py: Path helpers and constants — centralizes application paths (music library, cache, album art cache, logs), ensures directories exist, and handles OS-specific path quirks.

updater.py: Updater/service manager — checks for application updates, downloads update packages, validates signatures/hashes, and provides hooks to trigger update installation.
