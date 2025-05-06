import os
from pathlib import Path
import glob
import unicodedata
from typing import Optional
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
import random

class MediaFinder:
    """
    Handles finding cover art and artist images for the music browser.
    """
    
    def __init__(self, artist_images_dir: str = ""):
        """
        Initialize with artist images directory.
        
        Args:
            artist_images_dir (str): Directory containing artist images
        """
        self.artist_images_dir = artist_images_dir
        
    def find_cover_image(self, file_path: str) -> Optional[str]:
        """
        Find cover image for an audio file in its directory.
        
        Args:
            file_path (str): Path to the audio file
            
        Returns:
            Optional[str]: Path to cover image or None if not found
        """
        if not file_path or not os.path.exists(file_path):
            return None
            
        dir_path = Path(file_path).parent
        cover_names = ['cover', 'folder', 'front', 'album', 'artwork', 'art']
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        
        # First look for specific cover filenames
        for name in cover_names:
            for ext in image_extensions:
                cover_path = dir_path / f"{name}{ext}"
                if cover_path.exists():
                    return str(cover_path)
        
        # Then look for any image file
        for ext in image_extensions:
            for file in dir_path.glob(f"*{ext}"):
                return str(file)
                
        return None
        
    def find_artist_image(self, artist_name: str) -> Optional[str]:
        """
        Find artist image in the artist images directory.
        
        Args:
            artist_name (str): Name of the artist
            
        Returns:
            Optional[str]: Path to artist image or None if not found
        """
        if not self.artist_images_dir or not artist_name or not os.path.exists(self.artist_images_dir):
            return None
            
        # Normalize artist name (remove accents, lowercase)
        artist_name_norm = unicodedata.normalize('NFKD', artist_name.lower()) \
            .encode('ASCII', 'ignore').decode('utf-8')
            
        # Try different name formats
        name_formats = [
            artist_name,                      # Original
            artist_name.replace(' ', '_'),    # With underscores
            artist_name.replace(' ', '-'),    # With hyphens
            artist_name_norm,                 # Normalized
            artist_name_norm.replace(' ', '_'),
            artist_name_norm.replace(' ', '-')
        ]
        
        extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
        matching_files = []
        
        # Try all combinations
        for name in name_formats:
            # Exact matches with different extensions
            for ext in extensions:
                path = Path(self.artist_images_dir, f"{name}.{ext}")
                if os.path.exists(path):
                    matching_files.append(path)
            
            # Partial matches with glob
            for ext in extensions:
                pattern = Path(self.artist_images_dir, f"{name}*.{ext}")
                matching_files.extend(glob.glob(pattern))
        
        # Remove duplicates
        matching_files = list(set(matching_files))
        
        # Return a random image if multiple found
        if matching_files:
            return random.choice(matching_files)
            
        return None
        
    def load_image_to_label(self, image_path: str, label, default_text: str = "No image", max_size: int = 200):
        """
        Load an image into a QLabel.
        
        Args:
            image_path (str): Path to the image file
            label: QLabel to display the image
            default_text (str): Text to display if image not found
            max_size (int): Maximum width/height for the image
        """
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Corregida la forma de llamar a scaled con los argumentos correctos
            pixmap = pixmap.scaled(max_size, max_size, 
                                  Qt.AspectRatioMode.KeepAspectRatio, 
                                  Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(pixmap)
        else:
            label.setText(default_text)