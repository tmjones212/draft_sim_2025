from typing import Dict, Optional
from PIL import Image, ImageTk
import requests
from io import BytesIO
import tkinter as tk
import os
from ..utils.player_extensions import get_player_image_url, get_team_logo_url


class PlayerImageService:
    """Service for loading and caching player images"""
    
    def __init__(self):
        self.image_cache: Dict[str, ImageTk.PhotoImage] = {}
        self._loading_images: set = set()  # Track images currently being loaded
        self._failed_images: set = set()  # Track images that failed to load
        self._retry_count: Dict[str, int] = {}  # Track retry attempts
    
    def get_image(self, player_id: str, size: tuple = (40, 40)) -> Optional[ImageTk.PhotoImage]:
        """
        Get a player image from cache or return None if not cached.
        Use load_image_async to load new images.
        """
        cache_key = f"{player_id}_{size[0]}x{size[1]}"
        return self.image_cache.get(cache_key)
    
    def load_image_async(self, player_id: str, size: tuple = (40, 40), 
                        callback=None, widget: Optional[tk.Widget] = None):
        """
        Load a player image asynchronously.
        
        Args:
            player_id: Player ID for the image
            size: Tuple of (width, height) for the image
            callback: Optional callback function to call with the loaded image
            widget: Optional widget to schedule the callback on
        """
        cache_key = f"{player_id}_{size[0]}x{size[1]}"
        
        # Check if already cached
        if cache_key in self.image_cache:
            if callback:
                callback(self.image_cache[cache_key])
            return
        
        # Check if already loading
        if cache_key in self._loading_images:
            return
        
        # Check if this image has failed too many times
        if self._retry_count.get(cache_key, 0) >= 3:
            return
        
        self._loading_images.add(cache_key)
        
        # Use threading for truly async loading
        import threading
        thread = threading.Thread(
            target=self._load_image_threaded,
            args=(player_id, size, callback, widget)
        )
        thread.daemon = True
        thread.start()
    
    def _load_image_threaded(self, player_id: str, size: tuple, callback, widget: Optional[tk.Widget]):
        """Load image in a separate thread"""
        cache_key = f"{player_id}_{size[0]}x{size[1]}"
        
        try:
            # Check if this is a team logo request
            if player_id.startswith("team_"):
                team_abbr = player_id[5:]  # Remove "team_" prefix
                # First try to load from local file
                local_logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                              "assets", "team_logos", f"{team_abbr.lower()}.png")
                
                if os.path.exists(local_logo_path):
                    # Load from local file
                    img = Image.open(local_logo_path)
                    # Resize image to requested size
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    
                    # Schedule GUI update in main thread
                    if widget and widget.winfo_exists():
                        widget.after(0, lambda: self._update_image_cache(player_id, size, img, callback, widget))
                    return
                else:
                    # Fall back to URL if local file doesn't exist
                    image_url = get_team_logo_url(team_abbr)
                    print(f"Loading team logo from URL (local not found): {team_abbr} -> {image_url}")
            else:
                # First try to load player image from local file
                local_player_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                                "assets", "player_images", f"{player_id}.jpg")
                
                if os.path.exists(local_player_path) and os.path.getsize(local_player_path) > 0:
                    # Load from local file
                    img = Image.open(local_player_path)
                    # Resize image to requested size
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    
                    # Schedule GUI update in main thread
                    if widget and widget.winfo_exists():
                        widget.after(0, lambda: self._update_image_cache(player_id, size, img, callback, widget))
                    return
                else:
                    # Fall back to URL if local file doesn't exist or is empty
                    image_url = get_player_image_url(player_id)
            
            if not image_url:
                return
            
            response = requests.get(image_url, timeout=5)  # Increased timeout
            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                # Resize image to requested size
                img = img.resize(size, Image.Resampling.LANCZOS)
                
                # Schedule GUI update in main thread
                if widget and widget.winfo_exists():
                    widget.after(0, lambda: self._update_image_cache(player_id, size, img, callback, widget))
            else:
                print(f"Failed to load image for {player_id}: HTTP {response.status_code} from {image_url}")
                self._retry_count[cache_key] = self._retry_count.get(cache_key, 0) + 1
        except requests.exceptions.RequestException as e:
            print(f"Network error loading image for {player_id} ({image_url}): {e}")
            self._retry_count[cache_key] = self._retry_count.get(cache_key, 0) + 1
        except Exception as e:
            print(f"Error loading image for {player_id}: {e}")
            self._retry_count[cache_key] = self._retry_count.get(cache_key, 0) + 1
        finally:
            self._loading_images.discard(cache_key)
    
    def _update_image_cache(self, player_id: str, size: tuple, img: Image.Image, callback, widget: Optional[tk.Widget]):
        """Update cache and call callback in main thread"""
        cache_key = f"{player_id}_{size[0]}x{size[1]}"
        
        try:
            # Create PhotoImage in main thread
            photo = ImageTk.PhotoImage(img)
            
            # Cache it
            self.image_cache[cache_key] = photo
            
            # Call callback if provided
            if callback and widget and widget.winfo_exists():
                callback(photo)
        except Exception as e:
            print(f"Error updating image cache for {player_id}: {e}")
    
    def clear_cache(self):
        """Clear the image cache"""
        self.image_cache.clear()
        self._loading_images.clear()