from typing import Dict, List, Tuple, Any

class SearchParser:
    """
    Parser for music search queries with special syntax.
    Handles parsing queries with prefixes like 'a:' for artist, 'b:' for album, etc.
    """
    
    def __init__(self):
        """Initialize the search parser with defined filters and cache."""
        self.filters = {
            'a:': 'artist',
            'b:': 'album',
            'g:': 'genre',
            'l:': 'label',
            't:': 'title',
            'aa:': 'album_artist',
            'br:': 'bitrate',
            'd:': 'date',
            'w:': 'weeks',      # Last X weeks
            'm:': 'months',     # Last X months
            'y:': 'years',      # Last X years
            'am:': 'added_month', # Added in month X of year Y
            'ay:': 'added_year'   # Added in year Z
        }
        
        # Simple cache for frequent queries
        self.cache = {}
        self.cache_size = 20
        
    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a search query and extract filters and general terms.
        
        Args:
            query (str): The search query to parse
            
        Returns:
            Dict[str, Any]: Dictionary with 'filters' and 'general' keys
        """
        # Check cache first
        if query in self.cache:
            return self.cache[query]
            
        filters = {}
        general_terms = []
        current_term = ''
        i = 0
        
        while i < len(query):
            # Look for filter prefixes at the current position
            found_filter = False
            for prefix, field in self.filters.items():
                if query[i:].startswith(prefix):
                    # If we have accumulated a general term, add it
                    if current_term.strip():
                        general_terms.append(current_term.strip())
                        current_term = ''
                        
                    # Skip past the prefix
                    i += len(prefix)
                    
                    # Collect the value until the next filter or end
                    value = ''
                    while i < len(query):
                        # Check if another filter starts here
                        next_filter = False
                        for next_prefix in self.filters:
                            if query[i:].startswith(next_prefix):
                                next_filter = True
                                break
                        if next_filter:
                            break
                        value += query[i]
                        i += 1
                        
                    value = value.strip()
                    if value:
                        filters[field] = value
                    found_filter = True
                    break
                    
            if not found_filter and i < len(query):
                current_term += query[i]
                i += 1
                
        # Add the last term if any
        if current_term.strip():
            general_terms.append(current_term.strip())
            
        result = {
            'filters': filters,
            'general': ' '.join(general_terms)
        }
        
        # Update cache
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry if cache is full
            self.cache.pop(next(iter(self.cache)))
        self.cache[query] = result
        
        return result
        
    def build_sql_conditions(self, parsed_query: dict) -> Tuple[List[str], List[Any]]:
        """
        Build SQL WHERE conditions and parameters from parsed query.
        
        Args:
            parsed_query (dict): The parsed query from parse_query()
            
        Returns:
            Tuple[List[str], List[Any]]: Tuple of (conditions, parameters)
        """
        if not parsed_query:
            return [], []
            
        conditions = []
        params = []
        
        # Process specific filters
        for field, value in parsed_query['filters'].items():
            if field in ['weeks', 'months', 'years']:
                try:
                    value = int(value)
                    if field == 'weeks':
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' weeks')")
                    elif field == 'months':
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' months')")
                    else:  # years
                        conditions.append("s.last_modified >= datetime('now', '-' || ? || ' years')")
                    params.append(value)
                except ValueError:
                    print(f"Invalid value for {field}: {value}")
                    continue
            elif field == 'added_month':
                try:
                    month, year = value.split('/')
                    month = int(month)
                    year = int(year)
                    conditions.append("strftime('%m', s.last_modified) = ? AND strftime('%Y', s.last_modified) = ?")
                    params.extend([f"{month:02d}", str(year)])
                except (ValueError, TypeError):
                    print(f"Invalid format for month/year: {value}")
                    continue
            elif field == 'added_year':
                try:
                    year = int(value)
                    conditions.append("strftime('%Y', s.last_modified) = ?")
                    params.append(str(year))
                except ValueError:
                    print(f"Invalid year: {value}")
                    continue
            elif field == 'bitrate':
                # Handle bitrate ranges (>192, <192, =192)
                if value.startswith('>'):
                    conditions.append(f"s.{field} > ?")
                    params.append(int(value[1:]))
                elif value.startswith('<'):
                    conditions.append(f"s.{field} < ?")
                    params.append(int(value[1:]))
                else:
                    conditions.append(f"s.{field} = ?")
                    params.append(int(value))
            else:
                conditions.append(f"s.{field} LIKE ?")
                params.append(f"%{value}%")
                
        # Process general search terms
        if parsed_query['general']:
            general_fields = ['artist', 'title', 'album', 'genre', 'label', 'album_artist']
            general_conditions = []
            for field in general_fields:
                general_conditions.append(f"s.{field} LIKE ?")
                params.append(f"%{parsed_query['general']}%")
            if general_conditions:
                conditions.append(f"({' OR '.join(general_conditions)})")
                
        return conditions, params