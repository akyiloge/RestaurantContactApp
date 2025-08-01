from difflib import SequenceMatcher
import json
import gc
import os

class BrizoDataProcessor:
    """
    A helper class for processing, enriching, and filtering Brizo data.
    """

    def filter_clients(self, data):
        """
        Filters out objects from JSON data where associated_with matches client list

        Args:
            data: Dictionary with restaurant names as keys and lists of contact objects as values

        Returns:
            Filtered dictionary with same structure
        """
        # Client list
        clients = [
            "foodieforall", "repeatmd", "parkwood entertainment", "moneylion", "svb leerink"
        ]

        filtered_data = {}

        # Iterate through dictionary
        for restaurant_name, contacts in data.items():
            filtered_contacts = []

            # Filter each contact in the list
            for contact in contacts:
                associated_with_lower = contact.get("associated_with", "").lower().strip()

                # If associated_with is not in client list, keep the object
                if associated_with_lower not in clients:
                    filtered_contacts.append(contact)

            # Only add restaurant if it has remaining contacts after filtering
            if filtered_contacts:
                filtered_data[restaurant_name] = filtered_contacts

        return filtered_data

    def load_brizo_data(self, file_path):
        """
        Load Brizo data from large JSON file

        Args:
            file_path: Path to the Brizo JSON file

        Returns:
            List of Brizo objects
        """
        print("Loading Brizo data...")
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                brizo_data = json.load(file)
            print(f"Loaded {len(brizo_data)} Brizo entries")
            return brizo_data
        except Exception as e:
            print(f"Error loading Brizo data: {e}")
            return []

    def create_and_save_business_index(self, brizo_file_path, index_file_path):
        """
        Create business name index from Brizo data and save to file

        Args:
            brizo_file_path: Path to the Brizo JSON file
            index_file_path: Path where the index will be saved

        Returns:
            Dictionary mapping lowercase business names to list of entries
        """
        print("Creating business name index from original data...")

        # Load original data
        brizo_data = self.load_brizo_data(brizo_file_path)
        if not brizo_data:
            return {}

        # Create index
        index = {}
        for entry in brizo_data:
            business_name = entry.get('business_name', '').lower().strip()
            if business_name:
                if business_name not in index:
                    index[business_name] = []
                index[business_name].append(entry)

        print(f"Indexed {len(index)} unique business names")

        # Save index to file
        print(f"Saving index to {index_file_path}...")
        try:
            with open(index_file_path, 'w', encoding='utf-8') as file:
                json.dump(index, file, ensure_ascii=False, indent=2)
            print("Index saved successfully!")
        except Exception as e:
            print(f"Error saving index: {e}")
            return {}

        # Clear original data from memory
        del brizo_data
        gc.collect()
        print("Original data cleared from memory")

        return index

    def load_business_index(self, index_file_path):
        """
        Load business name index from file

        Args:
            index_file_path: Path to the saved index file

        Returns:
            Dictionary mapping lowercase business names to list of entries
        """
        print(f"Loading business index from {index_file_path}...")
        try:
            with open(index_file_path, 'r', encoding='utf-8') as file:
                index = json.load(file)
            print(f"Loaded index with {len(index)} unique business names")
            return index
        except Exception as e:
            print(f"Error loading index: {e}")
            return {}

    def get_or_create_business_index(self, brizo_file_path, index_file_path=None):
        """
        Get business index - load from file if exists, otherwise create and save

        Args:
            brizo_file_path: Path to the Brizo JSON file
            index_file_path: Path for the index file (defaults to brizo_file_path with .index.json)

        Returns:
            Dictionary mapping lowercase business names to list of entries
        """
        if index_file_path is None:
            # Default index file path
            base_name = os.path.splitext(brizo_file_path)[0]
            index_file_path = f"{base_name}.index.json"

        # Check if index file exists
        if os.path.exists(index_file_path):
            print("Index file found, loading...")
            return self.load_business_index(index_file_path)
        else:
            print("Index file not found, creating new index...")
            return self.create_and_save_business_index(brizo_file_path, index_file_path)

    def similarity(a, b):
        """Calculate similarity between two strings"""
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def find_matching_businesses(self, associated_with, business_index):
        """
        Find matching businesses using index and similarity matching

        Args:
            associated_with: The business name to search for
            business_index: Index of business names

        Returns:
            List of matching Brizo entries
        """
        associated_with_lower = associated_with.lower().strip()
        matches = []

        # Direct exact match
        if associated_with_lower in business_index:
            matches.extend(business_index[associated_with_lower])

        # Partial and similarity matching for remaining cases
        if not matches:
            for business_name, entries in business_index.items():
                # Partial match or high similarity
                if (associated_with_lower == business_name
                        # or business_name in associated_with_lower
                        # or self.similarity(associated_with_lower, business_name) > 0.85
                    ):
                    matches.extend(entries)

                    # Limit matches to prevent too many results
                    if len(matches) > 10:
                        break

        return matches

    def enrich_with_brizo_data(self, existing_data, brizo_file_path, index_file_path=None):
        """
        Enrich existing contact data with Brizo data using indexed lookup

        Args:
            existing_data: Dictionary with restaurant names as keys and contact lists as values
            brizo_file_path: Path to the Brizo JSON file
            index_file_path: Path to the index file (optional)

        Returns:
            Enriched data dictionary
        """
        # Get or create business index
        business_index = self.get_or_create_business_index(brizo_file_path, index_file_path)

        if not business_index:
            print("No business index available, returning original data")
            return existing_data

        enriched_data = {}
        total_restaurants = len(existing_data)
        processed = 0

        for restaurant_name, contacts in existing_data.items():
            processed += 1
            # print(f"Processing {processed}/{total_restaurants}: {restaurant_name}")

            # Tüm mevcut contact'ların email ve name'lerini topla (duplicate kontrolü için)
            all_existing_emails = set()
            all_existing_names = set()

            for contact in contacts:
                if contact.get('email'):
                    all_existing_emails.add(contact.get('email').lower().strip())
                if contact.get('name'):
                    all_existing_names.add(contact.get('name').lower().strip())

            enriched_contacts = []

            for contact in contacts:
                # Start with original contact
                enriched_contact = contact.copy()

                # Search for matching business in Brizo data
                associated_with = contact.get('associated_with', '').strip()

                if associated_with:
                    matching_brizo_entries = self.find_matching_businesses(associated_with, business_index)

                    if matching_brizo_entries:
                        # print(f"  Found {len(matching_brizo_entries)} matches for '{associated_with}'")

                        # Check if current contact exists in Brizo data (by name or email match)
                        current_contact_name = enriched_contact.get('name', '').lower().strip()
                        current_contact_email = enriched_contact.get('email', '').lower().strip()

                        contact_found_in_brizo = False

                        # Try to find current contact in Brizo data and enrich it
                        for brizo_entry in matching_brizo_entries:
                            brizo_contact = brizo_entry.get('contact', {})
                            if brizo_contact:
                                brizo_name = brizo_contact.get('name', '').lower().strip()
                                brizo_email = brizo_contact.get('email', '').lower().strip()

                                # Check if this Brizo contact matches current contact
                                name_match = brizo_name and current_contact_name and (
                                        brizo_name == current_contact_name
                                    # or self.similarity(brizo_name, current_contact_name) > 0.8
                                )
                                email_match = brizo_email and current_contact_email and brizo_email == current_contact_email

                                if name_match or email_match:
                                    # Enrich existing contact with Brizo data
                                    if brizo_contact.get('email'):
                                        enriched_contact['email_brizo'] = brizo_contact['email']
                                    if brizo_contact.get('phone'):
                                        enriched_contact['phone_brizo'] = brizo_contact['phone']
                                    if brizo_contact.get('title') or brizo_contact.get('role'):
                                        enriched_contact['title_brizo'] = brizo_contact.get('title',
                                                                                            brizo_contact.get('role',
                                                                                                              ''))

                                    enriched_contact['location_address'] = brizo_entry.get('location_address', '')
                                    enriched_contact['brizo_id'] = brizo_contact.get('id', '')

                                    contact_found_in_brizo = True
                                    # print(f"    Enriched existing contact: {enriched_contact['name']}")
                                    break

                # Orijinal contact'ı ekle (sadece bir kere)
                enriched_contacts.append(enriched_contact)

            # Şimdi tüm restaurant'ın contact'ları için Brizo'dan YENİ contact'ları bul
            for contact in contacts:
                associated_with = contact.get('associated_with', '').strip()

                if associated_with:
                    matching_brizo_entries = self.find_matching_businesses(associated_with, business_index)

                    if matching_brizo_entries:
                        for brizo_entry in matching_brizo_entries:
                            brizo_contact = brizo_entry.get('contact', {})

                            if brizo_contact:
                                brizo_email = brizo_contact.get('email', '').lower().strip()
                                brizo_name = brizo_contact.get('name', '').lower().strip()

                                # Check if this is a completely NEW contact (not in existing data)
                                is_new_contact = True

                                if brizo_email and brizo_email in all_existing_emails:
                                    is_new_contact = False
                                if brizo_name and brizo_name in all_existing_names:
                                    is_new_contact = False

                                if is_new_contact:
                                    new_contact = {
                                        'name': brizo_contact.get('name', brizo_contact.get('first_name',
                                                                                            '') + ' ' + brizo_contact.get(
                                            'last_name', '')).strip(),
                                        'associated_with': contact['associated_with'],  # Keep original associated_with
                                        'confidence': 'HIGH',  # Since it's from external source
                                        'source': 'Brizo',
                                        'location_address': brizo_entry.get('location_address', ''),
                                        'brizo_id': brizo_contact.get('id', '')
                                    }

                                    # Add Brizo data with _brizo suffix
                                    if brizo_contact.get('email'):
                                        new_contact['email_brizo'] = brizo_contact['email']
                                    if brizo_contact.get('phone'):
                                        new_contact['phone_brizo'] = brizo_contact['phone']
                                    if brizo_contact.get('title') or brizo_contact.get('role'):
                                        new_contact['title_brizo'] = brizo_contact.get('title',
                                                                                       brizo_contact.get('role', ''))

                                    # Clean up empty name
                                    if not new_contact['name'].strip():
                                        new_contact['name'] = 'Contact'

                                    enriched_contacts.append(new_contact)
                                    # print(
                                    #     f"    Added new contact: {new_contact['name']} ({new_contact.get('email_brizo', 'no email')})")

                                    # Track added emails/names to prevent duplicates within this restaurant
                                    if brizo_email:
                                        all_existing_emails.add(brizo_email)
                                    if brizo_name:
                                        all_existing_names.add(brizo_name)

            enriched_data[restaurant_name] = enriched_contacts

        print("Enrichment completed!")
        sorted_data = self.sort_contacts_by_source_and_confidence(enriched_data)
        return sorted_data

    # Helper functions for manual index management
    def create_index_only(self, brizo_file_path, index_file_path=None):
        """
        Only create and save the index without enrichment

        Args:
            brizo_file_path: Path to the Brizo JSON file
            index_file_path: Path where the index will be saved
        """
        if index_file_path is None:
            base_name = os.path.splitext(brizo_file_path)[0]
            index_file_path = f"{base_name}.index.json"

        index = self.create_and_save_business_index(brizo_file_path, index_file_path)
        print(f"Index creation completed. Index file: {index_file_path}")
        return index_file_path

    def check_index_stats(self, index_file_path):
        """
        Show statistics about the saved index

        Args:
            index_file_path: Path to the index file
        """
        index = self.load_business_index(index_file_path)
        if index:
            total_businesses = len(index)
            total_entries = sum(len(entries) for entries in index.values())
            print(f"Index Statistics:")
            print(f"  Unique business names: {total_businesses}")
            print(f"  Total entries: {total_entries}")
            print(f"  Average entries per business: {total_entries / total_businesses:.2f}")

    def sort_contacts_by_source_and_confidence(self, enriched_data):
        """
        Sort contacts within each restaurant: Email source first, then Brizo source
        Within each source, sort by confidence (HIGH > MEDIUM > LOW)

        Args:
            enriched_data: Dictionary with restaurant names as keys and contact lists as values

        Returns:
            Sorted enriched data dictionary
        """

        def get_sort_key(contact):
            """
            Create sort key for contact
            Returns tuple: (source_priority, confidence_priority)
            Lower numbers = higher priority
            """
            source = contact.get('source', 'Email')  # Default to Email if no source
            confidence = contact.get('confidence', 'MEDIUM')

            # Source priority: Email = 0, Brizo = 1
            source_priority = 0 if source == 'Email' else 1

            # Confidence priority: HIGH = 0, MEDIUM = 1, LOW = 2
            confidence_priority = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(confidence, 1)

            return (source_priority, confidence_priority)

        sorted_data = {}

        for restaurant_name, contacts in enriched_data.items():
            if contacts:
                # Sort contacts using the sort key
                sorted_contacts = sorted(contacts, key=get_sort_key)
                sorted_data[restaurant_name] = sorted_contacts

                # Debug logging
                # print(f"\nSorted contacts for {restaurant_name}:")
                for i, contact in enumerate(sorted_contacts):
                    source = contact.get('source', 'Email')
                    confidence = contact.get('confidence', 'MEDIUM')
                    name = contact.get('name', 'Unknown')
                    # print(f"  {i + 1}. {name} - {source} ({confidence})")
            else:
                sorted_data[restaurant_name] = contacts

        return sorted_data

if __name__ == "__main__":
    # Create an instance of the class
    processor = BrizoDataProcessor()

    # The call to create_index_only from the original code can now be done like this:
    # processor.create_index_only("../new_york_brizo.json")


    sample_data = {
        "sweetgreen": [
          {
            "name": "Mykaila Dudley",
            "associated_with": "sweetgreen",
            "email": "mykaila.dudley@sweetgreen.com",
            "phone": "917-563-6966",
            "title": "Staff",
            "confidence": "HIGH"
          },
          {
            "name": "Catering Team",
            "associated_with": "sweetgreen",
            "email": "catering@sweetgreen.com",
            "phone": "null",
            "title": "Catering Team",
            "confidence": "HIGH"
          }
        ]
    }

    # Call the method on the instance
    filtered_result = processor.enrich_with_brizo_data(sample_data, "../new_york_brizo")

    # Print to see the result
    print("\nFiltered Result:")
    print(json.dumps(filtered_result, indent=2))

    k = 2