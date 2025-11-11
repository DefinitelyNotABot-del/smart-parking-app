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
        print(f"Extracted - Vehicle: {vehicle_type}, Location: {location_query}")
        
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
                    score -= 3  # Penalty for wrong type
            
            # Match location (VERY HIGH priority - up to 20 points)
            if location_query:
                # Check if any word in location query matches spot location
                location_lower = spot['location'].lower()
                query_words = location_query.split()
                
                word_matches = 0
                for word in query_words:
                    if len(word) > 2:  # Skip short words
                        if word in location_lower:
                            word_matches += 1
                
                if word_matches > 0:
                    # Strong match for word presence
                    word_score = word_matches * 7
                    score += word_score
                    reasons.append(f"at {spot['location']}")
                else:
                    # Fuzzy match as fallback
                    similarity = self.fuzzy_match(location_query, location_lower)
                    if similarity > 0.4:
                        fuzzy_score = similarity * 10
                        score += fuzzy_score
                        reasons.append(f"near {spot['location']}")
            
            # Update best match
            if score > best_score:
                best_score = score
                best_spot = spot
                best_reasons = reasons
        
        # If no match at all, return error
        if not best_spot:
            return {
                'error': 'No spots available',
                'message': 'No parking spots found matching your criteria'
            }
        
        # If location was requested but score is too low, return error
        if location_query and best_score < 3:
            return {
                'error': 'Location not found',
                'message': f'No parking spots found near "{location_query}". Available locations: {", ".join(set([s["location"] for s in available_spots[:3]]))}'
            }
        
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
