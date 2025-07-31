import re
from typing import Dict, List, Any
from models import ContactInfo


class EmailAnalyzer:
    def __init__(self):
        self.generic_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'protonmail.com'
        ]


    def extract_sender_info(self, from_field: str) -> Dict[str, str]:
        match = re.match(r'^"?([^"<]+)"?\s*<([^<>]+)>$', from_field.strip())
        if match:
            name, email = match.groups()
            return {'name': name.strip(), 'email': email.strip()}
        else:
            return {'name': '', 'email': from_field.strip()}

    def analyze_domain_relevance(self, email: str, restaurant_name: str) -> Dict[str, Any]:

        domain = email.split('@')[1].lower() if '@' in email else ""
        restaurant_words = [w.lower() for w in re.findall(r'\w+', restaurant_name) if len(w) > 2]

        generic_domains = {
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'aol.com', 'icloud.com', 'protonmail.com'
        }

        analysis = {
            "is_restaurant_domain": False,
            "domain_match_score": 0.0,
            "is_generic": domain in generic_domains
        }

        if not analysis["is_generic"] and domain:
            domain_words = re.findall(r'\w+', domain)
            matched_words = sum(
                1 for rest_word in restaurant_words
                if any(rest_word in domain_word or domain_word in rest_word for domain_word in domain_words)
            )

            if matched_words > 0:
                analysis["is_restaurant_domain"] = True
                analysis["domain_match_score"] = round(matched_words / len(restaurant_words), 2)

        return analysis