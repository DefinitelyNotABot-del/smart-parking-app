"""
Lightweight NLP parser for parking search - no external API needed!
Uses pattern matching and fuzzy logic for natural language understanding.
"""
import re
from difflib import SequenceMatcher

class ParkingNLPParser:
    def __init__(self):
        # Vehicle type patterns
        self.vehicle_patterns = {
            'car': r'\b(car|sedan|suv|vehicle|auto|automobile)\b',
            'bike': r'\b(bike|motorcycle|motorbike|scooter|two[\s-]?wheeler)\b',
            'truck': r'\b(truck|lorry|heavy|large vehicle)\b'
        }
        
        # Location indicators
        self.location_keywords = [
            'near', 'close to', 'around', 'at', 'beside', 'next to', 
            'by', 'in', 'on', 'college', 'mall', 'hospital', 'station',
            'airport', 'downtown', 'center', 'market', 'building'
        ]
    
    def fuzzy_match(self, text1, text2):
        """Calculate fuzzy similarity between two strings"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def extract_vehicle_type(self, text):
        """Extract vehicle type from natural language"""
        text_lower = text.lower()
        
        for vehicle_type, pattern in self.vehicle_patterns.items():
            if re.search(pattern, text_lower):
                return vehicle_type
        
        return None
    
    def extract_location(self, text):
        """Extract location name from natural language"""
        text_lower = text.lower()
        
        # Look for location patterns
        for keyword in self.location_keywords:
            if keyword in text_lower:
                # Extract words after location keyword
                parts = text_lower.split(keyword)
                if len(parts) > 1:
                    location_part = parts[1].strip()
                    # Get first few meaningful words
                    words = location_part.split()[:3]
                    location = ' '.join(words).strip('.,!?')
                    return location
        
        return None
    
    def find_best_match(self, user_query, available_spots):
        """
        Find best parking spot using smart NLP - NO HALLUCINATIONS!
        Only returns spots that actually exist in the database.
        
        Args:
            user_query: Natural language query (e.g., "amc engineering college car")
            available_spots: List of dicts with 'spot_id', 'type', 'location', 'latitude', 'longitude'
        
        Returns:
            dict with 'spot_id', 'explanation', 'latitude', 'longitude' OR error dict
        """
        user_query_lower = user_query.lower()
        
        # Extract vehicle type
        vehicle_type = self.extract_vehicle_type(user_query)
        
        # Extract location preference
        location_query = self.extract_location(user_query)
        
        # Log what we extracted
        print(f"Extracted - Vehicle: {vehicle_type}, Location: '{location_query}'")
        print(f"Available locations: {[s['location'] for s in available_spots]}")
        
        # If no location extracted, try using the whole query
        if not location_query:
            location_query = user_query_lower
            # Remove vehicle type words
            for keywords in self.vehicle_patterns.values():
                location_query = re.sub(keywords, '', location_query).strip()
        
        # Score each spot
        best_spot = None
        best_score = -999
        best_reasons = []
        
        for spot in available_spots:
            score = 0
            reasons = []
            
            # Match vehicle type (HIGH priority - 10 points)
            if vehicle_type:
                if spot['type'] == vehicle_type:
                    score += 10
                    reasons.append(f"{vehicle_type} parking")
                else:
                    score -= 2  # Small penalty for wrong type
            else:
                # No vehicle type specified, use first available
                score += 2
            
            # Match location (VERY HIGH priority - up to 30 points)
            if location_query:
                location_lower = spot['location'].lower()
                
                # Split both query and location into words
                query_words = [w for w in location_query.split() if len(w) > 2]
                location_words = location_lower.split()
                
                # Count exact word matches
                word_matches = 0
                for qword in query_words:
                    for lword in location_words:
                        if qword in lword or lword in qword:
                            word_matches += 1
                            break
                
                if word_matches > 0:
                    # Strong match - give high score
                    word_score = word_matches * 10
                    score += word_score
                    reasons.append(f"at {spot['location']}")
                    print(f"Matched '{location_query}' to '{spot['location']}' with {word_matches} word matches (score: {word_score})")
                else:
                    # Try fuzzy match as fallback
                    similarity = self.fuzzy_match(location_query, location_lower)
                    if similarity > 0.3:  # Lower threshold
                        fuzzy_score = similarity * 15
                        score += fuzzy_score
                        reasons.append(f"near {spot['location']}")
                        print(f"Fuzzy matched '{location_query}' to '{spot['location']}' (similarity: {similarity:.2f}, score: {fuzzy_score})")
            
            print(f"Spot '{spot['location']}' ({spot['type']}): score = {score}")
            
            # Update best match
            if score > best_score:
                best_score = score
                best_spot = spot
                best_reasons = reasons
        
        # If no match at all, return first available
        if not best_spot:
            best_spot = available_spots[0]
            best_reasons = [f"Available {best_spot['type']} spot"]
            best_score = 1
        
        print(f"Best match: {best_spot['location']} with score {best_score}")
        
        # Generate explanation
        if best_reasons:
            explanation = ' '.join(best_reasons)
        elif vehicle_type:
            explanation = f"{vehicle_type.capitalize()} parking at {best_spot['location']}"
        else:
            explanation = f"Parking at {best_spot['location']}"
        
        return {
            'spot_id': best_spot['spot_id'],
            'explanation': explanation,
            'latitude': best_spot['latitude'],
            'longitude': best_spot['longitude'],
            'location': best_spot['location'],
            'type': best_spot['type']
        }

# Global parser instance
parser = ParkingNLPParser()
