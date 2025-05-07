def check_api_key(lastfm_api_key):
    """Checks if the Last.fm API key is valid"""
    print("Verifying Last.fm API key...")
    params = {
        'method': 'auth.getSession',
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    try:
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        # An incorrect API key should return a 403 error or an error message in JSON
        if response.status_code == 403:
            print("Invalid API key: Error 403 Forbidden")
            return False
        
        data = response.json()
        if 'error' in data and data['error'] == 10:
            print("Invalid API key: Authentication error")
            return False
        
        # If we reach here, the key seems valid even if the specific method requires more parameters
        print("API key appears valid")
        return True
        
    except Exception as e:
        print(f"Error verifying API key: {e}")
        return False

def get_with_retry(url, params, max_retries=3, retry_delay=1, timeout=10):
    """Performs an HTTP request with retries in case of error
    
    Args:
        url: URL to query
        params: Parameters for the request
        max_retries: Maximum number of retries
        retry_delay: Base wait time between retries (will increase exponentially)
        timeout: Maximum wait time for the request
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            
            # If rate limited, wait and retry
            if response.status_code == 429:  # Rate limit
                wait_time = int(response.headers.get('Retry-After', retry_delay * 2))
                print(f"Rate limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            
            return response
            
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            print(f"Error in attempt {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                # Exponential backoff
                sleep_time = retry_delay * (2 ** attempt)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    
    return None

def get_lastfm_scrobbles(lastfm_username, lastfm_api_key, from_timestamp=0, limit=200, progress_callback=None, filter_duplicates=True):
    """
    Gets scrobbles from Last.fm for a user from a specific timestamp.
    Implements caching for previously queried pages.
    
    Args:
        lastfm_username: Last.fm username
        lastfm_api_key: Last.fm API key
        from_timestamp: Timestamp to get scrobbles from
        limit: Maximum number of scrobbles per page
        progress_callback: Function for reporting progress (message, percentage)
        filter_duplicates: Whether to filter duplicate scrobbles
    """
    global cache_system
    lastfm_cache = cache_system.get('lastfm')
    
    all_tracks = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        # Update progress
        if progress_callback:
            progress = (page / total_pages * 15) if total_pages > 1 else 5
            progress_callback(f"Getting page {page} of {total_pages}", progress)
        else:
            print(f"Getting page {page} of {total_pages}")
        
        params = {
            'method': 'user.getrecenttracks',
            'user': lastfm_username,
            'api_key': lastfm_api_key,
            'format': 'json',
            'limit': limit,
            'page': page,
            'from': from_timestamp
        }
        
        # Check cache for this specific page
        cached_data = None
        if lastfm_cache:
            # Don't cache most recent scrobbles (first page if starting from 0)
            if not (from_timestamp == 0 and page == 1):
                cached_data = lastfm_cache.get('user.getrecenttracks', params)
        
        if cached_data:
            print(f"Using cached data for page {page} of scrobbles")
            data = cached_data
        else:
            try:
                response = get_with_retry('http://ws.audioscrobbler.com/2.0/', params)
                
                if not response or response.status_code != 200:
                    error_msg = f"Error getting scrobbles: {response.status_code if response else 'No response'}"
                    if progress_callback:
                        progress_callback(error_msg, 0)
                    else:
                        print(error_msg)
                        
                    if page > 1:  # If we've gotten some pages, return what we have
                        break
                    else:
                        return []
                
                data = response.json()
                
                # Save to cache all pages except the first if starting from 0
                # (because the first page contains the most recent scrobbles that change)
                if lastfm_cache and not (from_timestamp == 0 and page == 1):
                    lastfm_cache.put('user.getrecenttracks', params, data)
                
            except Exception as e:
                error_msg = f"Error processing page {page}: {str(e)}"
                if progress_callback:
                    progress_callback(error_msg, 0)
                else:
                    print(error_msg)
                
                if page > 1:  # If we've gotten some pages, return what we have
                    break
                else:
                    return []
        
        # Check if there are tracks
        if 'recenttracks' not in data or 'track' not in data['recenttracks']:
            break
        
        # Update total_pages
        total_pages = int(data['recenttracks']['@attr']['totalPages'])
        
        # Add tracks to the list
        tracks = data['recenttracks']['track']
        if not isinstance(tracks, list):
            tracks = [tracks]
        
        # Filter tracks that are currently being listened to (they don't have date)
        filtered_tracks = [track for track in tracks if 'date' in track]
        all_tracks.extend(filtered_tracks)
        
        # Report progress
        if progress_callback:
            progress = (page / total_pages * 15) if total_pages > 1 else 15
            progress_callback(f"Got page {page} of {total_pages} ({len(filtered_tracks)} tracks)", progress)
        else:
            print(f"Got page {page} of {total_pages} ({len(filtered_tracks)} tracks)")
        
        page += 1
        # Small pause to avoid overloading the API
        time.sleep(0.25)
    
    # Report total obtained
    if progress_callback:
        progress_callback(f"Retrieved {len(all_tracks)} scrobbles in total", 30)
    else:
        print(f"Retrieved {len(all_tracks)} scrobbles in total")
        
    # If requested, filter duplicates
    if filter_duplicates and all_tracks:
        if progress_callback:
            progress_callback("Filtering duplicate scrobbles...", 95)
        else:
            print("Filtering duplicate scrobbles...")
        
        filtered_tracks = filter_duplicate_scrobbles(all_tracks)
        
        if progress_callback:
            progress_callback(f"Retrieved {len(filtered_tracks)} unique scrobbles", 100)
        else:
            print(f"Retrieved {len(filtered_tracks)} unique scrobbles")
            
        return filtered_tracks
    
    # Only return the original all_tracks if filter_duplicates is False
    return all_tracks

def filter_duplicate_scrobbles(tracks):
    """
    Filters duplicate Last.fm scrobbles based on the same song and artist
    Prioritizes keeping the most recent scrobble
    
    Args:
        tracks: List of scrobbles from Last.fm
        
    Returns:
        Filtered list without duplicates
    """
    if not tracks:
        return []
    
    # We'll use a dictionary to keep only the most recent scrobble
    # for each unique artist+song combination
    unique_tracks = {}
    
    # Sort by timestamp in descending order (most recent first)
    sorted_tracks = sorted(tracks, key=lambda x: int(x['date']['uts']), reverse=True)
    
    for track in sorted_tracks:
        # Create a unique key for this song+artist
        key = (track['artist']['#text'].lower(), track['name'].lower())
        
        # Only save if this is the first time we're seeing this combination
        # (which will be the most recent due to sorting)
        if key not in unique_tracks:
            unique_tracks[key] = track
    
    # Convert the dictionary back to a list
    filtered_tracks = list(unique_tracks.values())
    
    # Re-sort by timestamp in ascending order for chronological processing
    filtered_tracks.sort(key=lambda x: int(x['date']['uts']))
    
    print(f"Filtered {len(tracks) - len(filtered_tracks)} duplicate scrobbles")
    print(f"Total unique scrobbles: {len(filtered_tracks)}")
    
    return filtered_tracks

def get_artist_info(artist_name, mbid, lastfm_api_key, lastfm_cache=None):
    """
    Gets detailed information about an artist from Last.fm, using cache and improved error handling
    
    Args:
        artist_name: Artist name
        mbid: Artist MusicBrainz ID (optional)
        lastfm_api_key: Last.fm API key
        lastfm_cache: Optional cache for Last.fm requests
        
    Returns:
        Dictionary with artist information or None if not found
    """
    if not artist_name or not lastfm_api_key:
        print(f"Artist name or API key not provided")
        return None
    
    # First try to get the correct name and MBID
    corrected_name, corrected_mbid = get_artist_correction(artist_name, lastfm_api_key, lastfm_cache)
    
    # Use the corrected MBID if it exists, otherwise the original
    mbid_to_use = corrected_mbid if corrected_mbid else mbid
    
    # Build query parameters
    params = {
        'method': 'artist.getInfo',
        'artist': corrected_name,
        'api_key': lastfm_api_key,
        'format': 'json'
    }
    
    if mbid_to_use:
        params['mbid'] = mbid_to_use
    
    # Check cache first
    if lastfm_cache:
        cached_result = lastfm_cache.get('artist.getInfo', params)
        if cached_result:
            print(f"Using cached data for Last.fm artist: {corrected_name}")
            return cached_result.get('artist')
    
    # Direct method first - more reliable and controlled
    try:
        print(f"Querying Last.fm API directly for artist: {corrected_name} (MBID: {mbid_to_use})")
        
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"HTTP error getting artist info {corrected_name}: {response.status_code}")
            print(f"Error response: {response.text[:200]}...")
            return None
        
        data = response.json()
        
        # Check if there's an error message in the JSON response
        if 'error' in data:
            error_code = data.get('error', 0)
            error_msg = data.get('message', 'Unknown error')
            print(f"Last.fm API error [{error_code}]: {error_msg}")
            
            # If the error is an invalid API key, don't try with pylast
            if error_code == 10 or 'Invalid API key' in error_msg:
                print("Invalid API key error, check your configuration")
                return None
                
            # For other errors, try with pylast as fallback
        else:
            # If no error, save to cache and return
            if 'artist' in data:
                print(f"Information obtained successfully for artist: {corrected_name}")
                
                # Save to cache
                if lastfm_cache:
                    lastfm_cache.put('artist.getInfo', params, data)
                    
                return data['artist']
            else:
                print(f"No information found for artist {corrected_name}")
    
    except requests.exceptions.RequestException as e:
        print(f"Connection error querying artist {corrected_name}: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response for artist {corrected_name}: {e}")
        print(f"Response received: {response.text[:200]}...")
    
    # If we reach here, try with pylast as a last resort
    try:
        print(f"Trying to get information with pylast for artist: {corrected_name}")
        import pylast
        
        # Verify API key before using pylast
        if len(lastfm_api_key) != 32:  # Last.fm API keys are usually 32 characters
            print("Last.fm API key seems invalid, skipping pylast method")
            return None
            
        network = pylast.LastFMNetwork(api_key=lastfm_api_key)
        
        # Decide whether to search by MBID or name
        if mbid_to_use:
            artist = network.get_artist_by_mbid(mbid_to_use)
        else:
            artist = network.get_artist(corrected_name)
        
        # Build a response similar to the API
        result = {}
        
        # Basic information
        result['name'] = artist.get_name()
        result['mbid'] = artist.get_mbid() or mbid_to_use
        result['url'] = artist.get_url()
        
        # Biography
        try:
            bio_content = artist.get_bio_content(language='es')
            if not bio_content:
                bio_content = artist.get_bio_content()
            
            bio_summary = artist.get_bio_summary(language='es')
            if not bio_summary:
                bio_summary = artist.get_bio_summary()
                
            result['bio'] = {
                'summary': bio_summary,
                'content': bio_content,
                'published': artist.get_bio_published_date()
            }
        except pylast.WSError as e:
            print(f"Pylast error getting biography: {e}")
            # If there's an error with the bio, leave it empty
            result['bio'] = {'summary': '', 'content': ''}
        
        # Tags
        try:
            top_tags = artist.get_top_tags(limit=10)
            tag_list = [{'name': tag.item.get_name(), 'url': tag.item.get_url()} for tag in top_tags]
            result['tags'] = {'tag': tag_list}
        except pylast.WSError as e:
            print(f"Pylast error getting tags: {e}")
            result['tags'] = {'tag': []}
        
        # Similar artists
        try:
            similar = artist.get_similar(limit=10)
            similar_list = [{'name': a.item.get_name(), 'url': a.item.get_url()} for a in similar]
            result['similar'] = {'artist': similar_list}
        except pylast.WSError as e:
            print(f"Pylast error getting similar artists: {e}")
            result['similar'] = {'artist': []}
        
        # Save to cache
        if lastfm_cache:
            cache_data = {'artist': result}
            lastfm_cache.put('artist.getInfo', params, cache_data)
            
        print(f"Artist information obtained using pylast: {result['name']}")
        return result
    
    except ImportError:
        print(f"pylast is not available, and the direct API failed")
    except pylast.WSError as e:
        error_details = str(e)
        print(f"Pylast error for artist {corrected_name}: {error_details}")
        
        # Show specific message for invalid API key
        if "Invalid API key" in error_details:
            print("The provided API key is not valid. Check your configuration.")
    except Exception as e:
        print(f"Unexpected error with pylast for artist {corrected_name}: {e}")
    
    # If we reach here, we couldn't get information
    print(f"Couldn't get information for artist {artist_name} by any method")
    return None

def get_artist_correction(artist_name, lastfm_api_key, lastfm_cache=None):
    """
    Uses the artist.getCorrection Last.fm API to get the 
    correct artist name and their MBID.
    
    Args:
        artist_name: Artist name to correct
        lastfm_api_key: Last.fm API key
        lastfm_cache: Optional cache for Last.fm requests
        
    Returns:
        Tuple (corrected_name, mbid) or (artist_name, None) if no correction
    """
    if not artist_name or not lastfm_api_key:
        return artist_name, None
    
    # Check cache first
    if lastfm_cache:
        cache_params = {
            'method': 'artist.getCorrection',
            'artist': artist_name
        }
        cached_result = lastfm_cache.get('artist.getCorrection', cache_params)
        if cached_result:
            print(f"Using cached data for artist correction: {artist_name}")
            return process_correction_response(cached_result, artist_name)
    
    # Use pylast if available
    try:
        import pylast
        network = pylast.LastFMNetwork(api_key=lastfm_api_key)
        artist = network.get_artist(artist_name)
        
        try:
            # Try to get corrections
            corrections = artist.get_correction()
            if corrections:
                corrected_artist = corrections[0]
                corrected_name = corrected_artist.get_name()
                mbid = corrected_artist.get_mbid()
                
                print(f"Correction found: '{artist_name}' -> '{corrected_name}' (MBID: {mbid})")
                
                # Save to cache
                if lastfm_cache:
                    response_data = {
                        'corrections': {'correction': [{'artist': {'name': corrected_name, 'mbid': mbid}}]}
                    }
                    lastfm_cache.put('artist.getCorrection', cache_params, response_data)
                
                return corrected_name, mbid
        except pylast.WSError:
            # If there's an error, try the alternative method
            pass
    except ImportError:
        # pylast is not available
        pass
    
    # Alternative method using requests directly
    try:
        params = {
            'method': 'artist.getCorrection',
            'artist': artist_name,
            'api_key': lastfm_api_key,
            'format': 'json'
        }
        
        response = requests.get('http://ws.audioscrobbler.com/2.0/', params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save to cache
            if lastfm_cache:
                lastfm_cache.put('artist.getCorrection', params, data)
            
            return process_correction_response(data, artist_name)
    except Exception as e:
        print(f"Error searching for correction for artist '{artist_name}': {e}")
    
    # If no correction is found or there's an error, return the original name
    return artist_name, None

def process_correction_response(data, original_name):
    """
    Processes the artist.getCorrection response
    
    Args:
        data: JSON response from the API
        original_name: Original artist name
        
    Returns:
        Tuple (corrected_name, mbid)
    """
    try:
        if 'corrections' in data and 'correction' in data['corrections']:
            corrections = data['corrections']['correction']
            
            # Can be a list or a single item
            if isinstance(corrections, list):
                correction = corrections[0]
            else:
                correction = corrections
            
            if 'artist' in correction:
                artist_data = correction['artist']
                corrected_name = artist_data.get('name', original_name)
                mbid = artist_data.get('mbid')
                
                # Only report if there's a difference
                if corrected_name.lower() != original_name.lower() or mbid:
                    print(f"Correction found: '{original_name}' -> '{corrected_name}' (MBID: {mbid})")
                
                return corrected_name, mbid
    except Exception as e:
        print(f"Error processing correction for '{original_name}': {e}")
    
    return original_name, None