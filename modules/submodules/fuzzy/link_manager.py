import webbrowser
from PyQt6.QtWidgets import QPushButton

class LinkManager:
    """Manages external links for artists and albums."""
    
    def __init__(self, parent):
        self.parent = parent
        # Esperar a que se inicialice la UI antes de conectar los botones
        # Este debería ejecutarse después de que loadUi haya sido llamado
        self.parent.ui_initialized.connect(self._connect_link_buttons)

    def _connect_link_buttons(self):
        """Connect all link buttons to their handlers."""
        from PyQt6.QtWidgets import QPushButton
        
        # Artist links
        link_buttons = [
            # Direct links from artists table
            ('spotify_url', self.parent.findChild(QPushButton, "spot_link_button")),
            ('youtube_url', self.parent.findChild(QPushButton, "yt_link_button")),
            ('musicbrainz_url', self.parent.findChild(QPushButton, "mb_link_button")),
            ('discogs_url', self.parent.findChild(QPushButton, "discogs_link_button")),
            ('rateyourmusic_url', self.parent.findChild(QPushButton, "rym_link_button")),
            ('wikipedia_url', self.parent.findChild(QPushButton, "wiki_link_button")),
            ('bandcamp_url', self.parent.findChild(QPushButton, "bc_link_button")),
            ('lastfm_url', self.parent.findChild(QPushButton, "lastfm_link_button")),
            
            # Links from artists_networks table
            ('allmusic', self.parent.findChild(QPushButton, "allmusic_link_button")),
            ('bandcamp', self.parent.findChild(QPushButton, "bc_link_button")),
            ('boomkat', self.parent.findChild(QPushButton, "boomkat_link_button")),
            ('facebook', self.parent.findChild(QPushButton, "fb_link_button")),
            ('twitter', self.parent.findChild(QPushButton, "twitter_link_button")),
            ('mastodon', self.parent.findChild(QPushButton, "mastodon_link_button")),
            ('bluesky', self.parent.findChild(QPushButton, "bluesky_link_button")),
            ('instagram', self.parent.findChild(QPushButton, "ig_link_button")),
            ('spotify', self.parent.findChild(QPushButton, "spot_link_button")),
            ('lastfm', self.parent.findChild(QPushButton, "lastfm_link_button")),
            ('wikipedia', self.parent.findChild(QPushButton, "wiki_link_button")),
            ('juno', self.parent.findChild(QPushButton, "juno_link_button")),
            ('soundcloud', self.parent.findChild(QPushButton, "soudcloud_link_button")),
            ('youtube', self.parent.findChild(QPushButton, "yt_link_button")),
            ('imdb', self.parent.findChild(QPushButton, "imdb_link_button")),
            ('progarchives', self.parent.findChild(QPushButton, "prog_link_button")),
            ('setlist_fm', self.parent.findChild(QPushButton, "setlist_link_button")),
            ('who_sampled', self.parent.findChild(QPushButton, "whosampled_link_button")),
            ('vimeo', self.parent.findChild(QPushButton, "vimeo_link_button")),
            ('resident_advisor', self.parent.findChild(QPushButton, "ra_link_button")),
            ('rateyourmusic', self.parent.findChild(QPushButton, "rym_link_button")),
            ('tumblr', self.parent.findChild(QPushButton, "tumblr_link_button")),
            ('myspace', self.parent.findChild(QPushButton, "myspace_link_button"))
        ]
        
        # Connect artist link buttons
        for link_type, button in link_buttons:
            if button:
                # Use a partial function to preserve the link_type value
                from functools import partial
                button.clicked.connect(partial(self._open_link, button))
        
        # Album links - similar structure to artist links
        album_link_buttons = [
            ('spotify_url', self.parent.findChild(QPushButton, "spot_album_link_button")),
            ('youtube_url', self.parent.findChild(QPushButton, "yt_album_link_button")),
            ('musicbrainz_url', self.parent.findChild(QPushButton, "mb_album_link_button")),
            ('discogs_url', self.parent.findChild(QPushButton, "discogs_album_link_button")),
            ('rateyourmusic_url', self.parent.findChild(QPushButton, "rym_album_link_button")),
            ('wikipedia_url', self.parent.findChild(QPushButton, "wiki_album_link_button")),
            ('bandcamp_url', self.parent.findChild(QPushButton, "bc_album_link_button")),
            ('lastfm_url', self.parent.findChild(QPushButton, "lastfm_album_link_button"))
        ]
        
        # Connect album link buttons
        for link_type, button in album_link_buttons:
            if button:
                # Use a partial function to preserve the link_type value
                button.clicked.connect(partial(self._open_link, button))
        
        # Find the group containers
        self.parent.artist_links_group = self.parent.findChild(QWidget, "artist_links_group")
        self.parent.album_links_group = self.parent.findChild(QWidget, "album_links_group")
    
    def update_artist_links(self, artist):
        """Update artist link buttons based on available links."""
        # Hide all buttons first
        self.hide_artist_links()
        
        # Show buttons for available links
        self._show_link_if_available(artist, 'spotify_url', self.parent.spot_link_button)
        self._show_link_if_available(artist, 'youtube_url', self.parent.yt_link_button)
        self._show_link_if_available(artist, 'musicbrainz_url', self.parent.mb_link_button)
        self._show_link_if_available(artist, 'discogs_url', self.parent.discogs_link_button)
        self._show_link_if_available(artist, 'rateyourmusic_url', self.parent.rym_link_button)
        self._show_link_if_available(artist, 'wikipedia_url', self.parent.wiki_link_button)
        self._show_link_if_available(artist, 'bandcamp_url', self.parent.bc_link_button)
        self._show_link_if_available(artist, 'lastfm_url', self.parent.lastfm_link_button)
        
        # Links from artists_networks table
        self._show_link_if_available(artist, 'allmusic', self.parent.allmusic_link_button)
        self._show_link_if_available(artist, 'bandcamp', self.parent.bc_link_button)
        self._show_link_if_available(artist, 'boomkat', self.parent.boomkat_link_button)
        self._show_link_if_available(artist, 'facebook', self.parent.fb_link_button)
        self._show_link_if_available(artist, 'twitter', self.parent.twitter_link_button)
        self._show_link_if_available(artist, 'mastodon', self.parent.mastodon_link_button)
        self._show_link_if_available(artist, 'bluesky', self.parent.bluesky_link_button)
        self._show_link_if_available(artist, 'instagram', self.parent.ig_link_button)
        self._show_link_if_available(artist, 'spotify', self.parent.spot_link_button)
        self._show_link_if_available(artist, 'lastfm', self.parent.lastfm_link_button)
        self._show_link_if_available(artist, 'wikipedia', self.parent.wiki_link_button)
        self._show_link_if_available(artist, 'juno', self.parent.juno_link_button)
        self._show_link_if_available(artist, 'soundcloud', self.parent.soudcloud_link_button)
        self._show_link_if_available(artist, 'youtube', self.parent.yt_link_button)
        self._show_link_if_available(artist, 'imdb', self.parent.imdb_link_button)
        self._show_link_if_available(artist, 'progarchives', self.parent.prog_link_button)
        self._show_link_if_available(artist, 'setlist_fm', self.parent.setlist_link_button)
        self._show_link_if_available(artist, 'who_sampled', self.parent.whosampled_link_button)
        self._show_link_if_available(artist, 'vimeo', self.parent.vimeo_link_button)
        self._show_link_if_available(artist, 'resident_advisor', self.parent.ra_link_button)
        self._show_link_if_available(artist, 'rateyourmusic', self.parent.rym_link_button)
        self._show_link_if_available(artist, 'tumblr', self.parent.tumblr_link_button)
        self._show_link_if_available(artist, 'myspace', self.parent.myspace_link_button)
    
    def update_album_links(self, album):
        """Update album link buttons based on available links."""
        # Hide all buttons first
        self.hide_album_links()
        
        # Show buttons for available links
        self._show_link_if_available(album, 'spotify_url', self.parent.spot_album_link_button)
        self._show_link_if_available(album, 'youtube_url', self.parent.yt_album_link_button)
        self._show_link_if_available(album, 'musicbrainz_url', self.parent.mb_album_link_button)
        self._show_link_if_available(album, 'discogs_url', self.parent.discogs_album_link_button)
        self._show_link_if_available(album, 'rateyourmusic_url', self.parent.rym_album_link_button)
        self._show_link_if_available(album, 'wikipedia_url', self.parent.wiki_album_link_button)
        self._show_link_if_available(album, 'bandcamp_url', self.parent.bc_album_link_button)
        self._show_link_if_available(album, 'lastfm_url', self.parent.lastfm_album_link_button)
    
    def hide_all_links(self):
        """Hide all link buttons."""
        self.hide_artist_links()
        self.hide_album_links()
    
    def hide_artist_links(self):
        """Hide all artist link buttons."""
        for button in self.parent.artist_links_group.findChildren(QPushButton):
            button.setVisible(False)
    
    def hide_album_links(self):
        """Hide all album link buttons."""
        for button in self.parent.album_links_group.findChildren(QPushButton):
            button.setVisible(False)
    
    def _show_link_if_available(self, item, link_key, button):
        """Show a link button if the corresponding link is available."""
        if item and item.get(link_key):
            button.setVisible(True)
            
            # Store the URL in the button's property
            button.setProperty('url', item[link_key])
        else:
            button.setVisible(False)
    
    def _open_artist_link(self, link_type):
        """Open the artist link in a web browser."""
        sender = self.parent.sender()
        if sender and sender.property('url'):
            url = sender.property('url')
            webbrowser.open(url)
    
    def _open_album_link(self, link_type):
        """Open the album link in a web browser."""
        sender = self.parent.sender()
        if sender and sender.property('url'):
            url = sender.property('url')
            webbrowser.open(url)

    def _open_link(self, button):
        """Open a link in the web browser."""
        url = button.property('url')
        if url:
            webbrowser.open(url)