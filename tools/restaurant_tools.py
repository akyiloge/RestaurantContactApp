from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

from gmail_service import GmailService
from email_utils import EmailAnalyzer
import json
import re
import os
from typing import List, Dict

class RestaurantContactTools:
    def __init__(self, gmail_credentials_info: Dict):
    # def __init__(self):
        self.gmail_service = GmailService(gmail_credentials_info)
        # self.gmail_service = GmailService()
        self.email_analyzer = EmailAnalyzer()
        self.found_emails = set()
        self.email_contacts_dict = {}

    def search_and_extract_contacts(self, restaurant_name: str) -> str:
        """Search emails and extract contacts"""
        self.found_emails.clear()

        unique_emails = []
        self.email_contacts_dict.clear()

        # If the file exists, use it
        # if os.path.exists("unique_addresses.json"):
        #     with open("unique_addresses.json", "r") as f:
        #         unique_emails = json.load(f)
        #
        # else:
        ignored_senders = ['noreply', 'donotreply', 'mailer-daemon', 'no-reply']
        exclusion_filter = " ".join([f'-from:{sender}' for sender in ignored_senders])
        exclusion_filter += " -unsubscribe"

        restaurant_name_cleaned = restaurant_name.lower().replace("'", "")#restaurant_name.lower()#.replace(" ", "").replace("&", "")

        queries = [
            f'{restaurant_name_cleaned} {exclusion_filter}'
        ]

        # queries = [
        #     f'"{restaurant_name}"',
        #     f'from:@{restaurant_name.lower().replace(" ", "").replace("&", "")}',
        #     f'subject:{restaurant_name}',
        # ]

        all_emails = []
        for query in queries:
            emails = self.gmail_service.search_emails(query, max_results=300)
            all_emails.extend(emails)

        if len(all_emails) < 20:
            newQuery = f'{restaurant_name}'
            emails = self.gmail_service.search_emails(newQuery, max_results=200)
            all_emails.extend(emails)

        all_emails = self.filter_emails_by_body_content(all_emails)

        # Remove duplicates
        seen_ids = set()

        for email in all_emails:
            if email['message_id'] not in seen_ids:
                unique_emails.append(email)
                seen_ids.add(email['message_id'])

        # with open("unique_addresses.json", "w") as f:
        #     json.dump(unique_emails, f, indent=2)


        if not unique_emails:
            return json.dumps({"restaurant": restaurant_name, "contacts": []})


        email_batch = []
        email_batch2 = []
        for idx, email in enumerate(unique_emails):
            if 'dmarc' in email['from'].lower():
                continue

            if email['thread_id'] == '19731e43a7acdb86':
                we = 2


            self.extract_contact_blocks(email['body'], email['from'], email['to'], self.email_contacts_dict, restaurant_name)


        finalList = self.email_contacts_dict #self.filter_emails_by_restaurant_name(self.email_contacts_dict, restaurant_name)
        batchFinal = self.generate_restaurant_contact_prompt(finalList, restaurant_name)

        if not batchFinal:
            return json.dumps({"restaurant": restaurant_name, "contacts": []})

        print("*********batch final**********")
        print(batchFinal)
        print("*********batch final**********")

        # with open("truncate_result.json", "w") as f:
        #     json.dump(email_batch, f, indent=2)


        # Tek LLM çağrısı ile tüm contactları çıkar
        return batchFinal
        # return self._extract_all_contacts_with_llm(
        #     batchFinal,
        #     restaurant_name
        # )

    def extract_contact_blocks(self, body: str, from_email: str, to_email: str, email_contacts_dict: dict, restaurant_name: str) -> list:\

        lines = body.split('\n') if body else []

        name1, email1 = self.parse_email_string(from_email)
        if email1 and 'foodie' not in email1.lower():
            if email1 not in email_contacts_dict:
                content = email1
                if name1:
                    content += f'\n{name1}'
                lines.append(content)

        name2, email2 = self.parse_email_string(to_email)
        if email2 and 'foodie' not in email2.lower():
            if email2 not in email_contacts_dict:
                content = email2
                if name2:
                    content += f'\n{name2}'
                lines.append(content)

        contact_blocks = []

        # Pattern'ler
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        # Telefon pattern'leri - çeşitli formatları destekler
        phone_patterns = [
            r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890, 123-456-7890
            r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',  # 123.456.7890
            r'\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1 (123) 456-7890
            r'\b\d{10,}\b',  # 1234567890 (10+ rakam)
            r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'  # Orijinal pattern'iniz
        ]

        def calculate_score(text, contacts, phonesList):
            """Block'un quality score'unu hesapla"""
            lines = text.split('\n')

            # İsim kontrolü (Mykaila Dudley gibi)
            has_name = any(re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', line) for line in lines)

            # Title kontrolü
            has_title = any(re.search(r'Manager|Director|Sales|Catering|Chef|Owner|Specialist', line, re.I) for line in lines)

            # Signature indicator'ları
            has_signature = any(re.search(r'(From:|Date:|Subject:|Sent from|Best|Regards|Thanks)', line, re.I) for line in lines)

            # Restaurant domain email kontrolü
            #restaurant_emails = [c for c in contacts if '@' in c and not any(generic in c for generic in ['gmail', 'yahoo', 'hotmail', 'foodieforall'])]

            # Skor hesaplama
            score = 0
            score += len(contacts) * 2  # Her contact 2 puan
            score += len(phonesList) * 5  # Her phone 5 puan
            score += 3 if has_name else 0
            score += 2 if has_title else 0
            score += 1 if has_signature else 0
            #score += 3 if restaurant_emails else 0  # Restaurant email bonus

            # Quote işaretleri penalty (>>> veya >)
            quote_count = sum(1 for line in lines if line.strip().startswith(('>', '>>>')))
            if quote_count > len(lines) * 0.5:  # Yarıdan fazlası quote ise
                score -= 2

            return score

        # Contact içeren satırları bul
        contact_indices = []
        for i, line in enumerate(lines):
            emails = re.findall(email_pattern, line, re.IGNORECASE)

            # Multi-pattern telefon kontrolü
            phones = []
            for phone_pattern in phone_patterns:
                found_phones = re.findall(phone_pattern, line)
                # Sadece yeterli rakam içeren telefon numaralarını al
                for phone in found_phones:
                    numbers = re.findall(r'\d', phone)
                    # Sadece rakam, tire, parantez, boşluk ve + içermelidir

                    if len(numbers) >= 10 and phone != "917-563-6966" and phone != "310-721-8481" and phone != "973-901-1877O":
                        phones.append(phone)

            # Remove Duplicate phone numberes
            phones = list(set(phones))

            if any('foodieforall' in e.lower() for e in emails):
            #if any('foodieforall' in e.lower() for e in emails) or not any(restaurant_name.lower() in e.lower() for e in emails):
                continue


            if emails or phones:
                contact_indices.append({
                    'index': i,
                    'emails': emails,
                    'phones': phones,
                    'richness': len(emails) + len(phones)  # Zenginlik skoru
                })

        # Overlapping block'ları birleştir
        processed_indices = set()

        for contact in sorted(contact_indices, key=lambda x: x['richness'], reverse=True):
            i = contact['index']

            # Bu satır zaten işlendiyse skip
            if i in processed_indices:
                continue

            # Context window (5 lines up, 5 lines down)
            start = max(0, i - 6)
            end = min(len(lines), i + 10)

            for j in range(start, end):
                processed_indices.add(j)

            block_lines = []
            block_contacts = set()
            phone_list = set()

            for j in range(start, end):
                line = lines[j].strip()
                if line:
                    block_lines.append(line)
                    # Bu satırdaki contactları topla
                    for email in re.findall(email_pattern, line, re.IGNORECASE):
                        if 'foodieforall' not in email.lower():
                            block_contacts.add(email.lower())

                    # Multi-pattern telefon kontrolü block içi
                    for phone_pattern in phone_patterns:
                        found_phones = re.findall(phone_pattern, line)
                        for phone in found_phones:
                            numbers = re.findall(r'\d', phone)
                            if self.normalize_phone(phone) and phone != "917-563-6966" and phone != "310-721-8481" and phone != "973-901-1877":
                                block_contacts.add(re.sub(r'\D', '', phone))
                                phone_list.add(re.sub(r'\D', '', phone))

            if block_lines and len(block_contacts) > 0:
                block_text = '\n'.join(block_lines)

                # if '1621974410' in phone_list:
                #     d = 2

                # Calculate quality score
                quality_score = calculate_score(block_text, block_contacts, phone_list)

                # Minimum quality check
                if quality_score >= 2:  # At least 2 contact info or 1 contact and 1 name

                    primary_emails = [contact for contact in block_contacts if '@' in contact]
                    primary_phones = [contact for contact in block_contacts if '@' not in contact]

                    if primary_emails:
                        restaurant_emails = [e for e in primary_emails if restaurant_name.lower() in e]
                        if restaurant_emails:
                            dict_key = restaurant_emails[0]
                        else:
                            dict_key = sorted(primary_emails)[0]  # Fallback

                        # elif primary_phones:
                        #     dict_key = primary_phones[0]


                        should_add = False

                        if dict_key not in email_contacts_dict:
                            should_add = True
                        else:
                            existing_score = email_contacts_dict[dict_key]['score']
                            if quality_score > existing_score:
                                should_add = True

                        if should_add:
                            if len(block_text) > 1000:
                                block_text = block_text[:1000] + "... [truncated]"

                            email_contacts_dict[dict_key] = {
                                'primary_contact': dict_key,
                                'all_contacts': list(block_contacts),
                                'content': block_text,
                                'score': quality_score,
                                'emails': primary_emails,
                                'phones': primary_phones
                            }




        # current_blocks = []
        # for key, data in email_contacts_dict.items():
        #     current_blocks.append({
        #         'text': data['content'],
        #         'score': data['score'],
        #         'contacts': data['all_contacts']
        #     })
        #
        # current_blocks.sort(key=lambda x: x['score'], reverse=True)
        # return [block['text'] for block in current_blocks[:5]]


    def filter_emails_by_body_content(self, emails):
        """
        Filter out emails containing specific phrases in body
        """
        excluded_phrases = [
            "Potential Duplicate Restaurants",
            "unsubscribe"
        ]

        filtered_emails = []
        for email in emails:
            body = email.get('body', '').lower()

            # Check if any excluded phrase exists in body
            should_exclude = any(phrase.lower() in body for phrase in excluded_phrases)

            if not should_exclude:
                filtered_emails.append(email)

        return filtered_emails


    def parse_email_string(self, email_string):
        """
        parse email
        """
        if not email_string:
            return None, None

        # Pattern: "Name <email@domain.com>" formatı
        match = re.match(r'^(.+?)\s*<(.+?)>$', email_string.strip())

        if match:
            # name and email exists
            name = match.group(1).strip()
            email = match.group(2).strip()
            return name, email
        else:
            # just email
            return None, email_string.strip()


    def normalize_phone(self, phone: str) -> str | None:
        digits_only = re.sub(r'[^0-9]', '', phone)

        if len(digits_only) == 11 and digits_only.startswith('1'):
            digits_only = digits_only[1:]

        if len(digits_only) == 10:
            return digits_only

        return None  # geçerli değil

    def filter_emails_by_restaurant_name(self, email_contacts_dict: dict, restaurant_name: str,
                                         min_word_matches: int = 1) -> dict:
        """
        Splits the restaurant name and filters emails that contain these words (searches only in dict_key)

        Args:
            email_contacts_dict: Dictionary of email contacts
            restaurant_name: Restaurant name, e.g., "The Little Pie Company"
            min_word_matches: Minimum number of word matches required (default: 1)

        Returns:
            Filtered email dictionary
        """


        # Stop words - bunları ignore et
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'co', 'company', 'inc', 'llc', 'corp', 'ltd',
            'restaurant', 'cafe', 'kitchen', 'grill', 'bar', 'pub'
        }

        # Restaurant name'i split et ve temizle
        words = restaurant_name.lower().split()
        meaningful_words = []

        for word in words:
            if word.lower() not in stop_words:
                # Özel karakterleri temizle (kesme işareti, noktalama vb.)
                cleaned_word = re.sub(r"[^\w]", "", word)  # Sadece harf ve rakamları bırak
                if len(cleaned_word) >= 3:  # 3+ karakter
                    meaningful_words.append(cleaned_word)

        print(f"Restaurant: {restaurant_name}")
        print(f"Search words: {meaningful_words}")
        print("-" * 50)

        filtered_emails = {}

        for dict_key, contact_data in email_contacts_dict.items():
            search_text = re.sub(r"[^\w@.]", "", dict_key.lower())  # Email için @ ve . bırak

            matching_words = []
            for word in meaningful_words:
                if word in search_text:
                    matching_words.append(word)

            if len(matching_words) >= min_word_matches:
                contact_data_copy = contact_data.copy()
                contact_data_copy['matching_words'] = matching_words
                contact_data_copy['match_count'] = len(matching_words)
                contact_data_copy['match_percentage'] = len(matching_words) / len(meaningful_words) * 100

                filtered_emails[dict_key] = contact_data_copy

                # print(f"✓ MATCH: {dict_key}")
                # print(f"  Matching words: {matching_words}")
                # print(f"  Match count: {len(matching_words)}/{len(meaningful_words)}")
                # print(f"  Score: {contact_data['score']}")
                # print()

        sorted_emails = dict(sorted(
            filtered_emails.items(),
            key=lambda x: (x[1]['match_count'], x[1]['score']),
            reverse=True
        ))

        return sorted_emails

    def generate_restaurant_contact_prompt(self, final_list: dict, restaurant_name: str) -> str:
        if not final_list:
            return f"No relevant contact information found for {restaurant_name}."

        email_content_blocks = []

        sorted_items = sorted(final_list.items(), key=lambda x: x[1].get('score', 0), reverse=True)

        for idx, (email_key, contact_data) in enumerate(sorted_items, 1):
            # primary_contact = contact_data.get('primary_contact', '')
            # all_contacts = contact_data.get('all_contacts', [])
            content = contact_data.get('content', '')
            score = contact_data.get('score', 0)
            emails = contact_data.get('emails', [])
            phones = contact_data.get('phones', [])

            contact_lines = []
            if emails:
                contact_lines.append(f"Emails: {', '.join(emails)}")
            if phones:
                contact_lines.append(f"Phones: {', '.join(phones)}")

            contacts_info = '\n'.join(contact_lines)

            block = f"""=== EMAIL BLOCK {idx} (Score: {score}) ===
            {contacts_info}
        
            CONTENT:
            {content}
            {'=' * 50}"""

            email_content_blocks.append(block)

        # Concatenate blocks
        return '\n'.join(email_content_blocks)


    def analyze_email_blocks_tool(self, email_blocks: str, restaurant_name: str) -> str:
        """Analyze Email blocks and extract staff contacts"""
        llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

        restaurant_keywords = restaurant_name.lower().replace("'", "").replace(" ", "")

        print("9" * 90)
        print(email_blocks)

        prompt = f"""TASK: Extract ONLY restaurant staff contacts for "{restaurant_name}" and related restaurant group entities.

        **INSTRUCTION FLOW:**
        First, you will think step-by-step inside a `<thinking>` block. You will list all potential contacts and then filter them based on the rules.
        Second, AFTER the thinking block, you will provide the final, clean JSON output.

        ---

        **STEP 1: THINKING PROCESS (Mandatory)**

        Inside a `<thinking>` block, follow this exact process:
        1. **List ALL Candidates:** Go through EVERY EMAIL BLOCK systematically and list EVERY potential contact (name, email, phone) you find, including partial names and email-only entries.
        2. **Analyze Context:** For each candidate, examine the email context to determine if they are restaurant staff, client, or Foodie For All employee.
        3. **Check Restaurant Group Relationships:** Look for administrative/management companies that handle operations for the target restaurant.
        4. **Filter and Justify:** For EACH candidate, check them against the rules below. State clearly whether you are KEEPING or DISCARDING the candidate and provide a one-sentence justification.
        5. **Final List:** Summarize the candidates you are keeping.

        ---

        **STRICT EXCLUSION RULES:**

        1. **Foodie For All Staff:** DISCARD if the person is a Foodie For All employee.
           - Known names: `BJ Meltzer`, `Oge Akyil`, `Harper Flood`, `Caroline Anderson`, `Corey Light`
           - Email domains: `@foodieforall.com`, `@ffaadmin.com`
           - **Justification:** "Discarding [Name] because they are a Foodie For All employee."

        2. **Clients:** DISCARD if the person is a client ordering food.
           - Listed as `Client Name:` in order confirmations
           - Email domains from client companies (e.g., `@torys.com`, `@zip.co`, `@cvc.com`, etc.)
           - **Justification:** "Discarding [Name] because they are a client ordering food."

        3. **Non-Restaurant Entities:** DISCARD payment processors, generic services, etc.
           - Examples: `@authorize.net`, `@doordash.com`, generic support emails
           - **Justification:** "Discarding [Name] because they are not restaurant-related staff."

        ---

        **RESTAURANT GROUP IDENTIFICATION RULES:**

        1. **Direct Restaurant Staff:** KEEP if clearly associated with the target restaurant.
           - Email contains restaurant name (e.g., `pokebowlcatering@gmail.com` for Poke Bowl)
           - Person communicates FROM the restaurant TO Foodie For All
           - Clear restaurant titles or operational context

        2. **Restaurant Group/Management Staff:** KEEP if they handle operations for the target restaurant.
           - Look for companies that process payments, coordinate orders, or handle administrative functions for the target restaurant
           - Examples: If extracting "Poke Bowl" staff, include Black Dolphin Group staff who clearly handle Poke Bowl operations
           - Check for mixed email threads where both restaurant and management company emails appear together
           - Look for patterns like: "Mayra from [Management Company] will handle payment for [Target Restaurant] order"

        3. **Operational Integration Signals:**
           - Same email threads containing both restaurant and management company contacts
           - Management company staff sending payment links for restaurant orders
           - Coordination emails between management company and Foodie For All about restaurant orders
           - Administrative staff scheduling or confirming restaurant deliveries

        ---

        **VERIFICATION RULES:**
        - **HIGH Confidence:** Email contains restaurant name OR person clearly handles operations for the target restaurant
        - **MEDIUM Confidence:** Person from management company with clear operational role for the restaurant
        - **LOW Confidence:** Weak association but hints at restaurant/group role

        ---

        **EMAIL BLOCKS:**
        {email_blocks}

        ---

        **STEP 2: FINAL OUTPUT**
        After the `<thinking>` block, provide ONLY the JSON array of verified "{restaurant_name}" and related restaurant group staff.

        **JSON Format:**
        [
          {{
            "name": "Name",
            "associated_with": "associated with",
            "email": "email@domain.com", 
            "phone": "phone_number",
            "title": "title_or_company_if_available",  
            "confidence": "HIGH/MEDIUM/LOW"
          }}
        ]

        **Title Field Examples:**
        - "Catering Manager" (if role is clear)
        - "Black Dolphin Group - Administrative" (if from management company)
        - "Owner" (if role is specified)
        - "Staff" (if role unclear but clearly restaurant-related)
        """

        try:
            response = llm.invoke(prompt)
            print("|||" * 25)
            print(response.content)
            print("|||" * 25)
            return response.content
        except Exception as e:
            return json.dumps([])





    def create_tools(self):
        """Create tools for agents"""
        return [
            Tool(
                name="Search_Restaurant_Emails",
                func=self.search_and_extract_contacts,
                description="Search emails for a restaurant and return email blocks. Use this to get email data for a restaurant. Input should be the restaurant name as a string."
            ),
            Tool(
                name="Analyze_Email_Blocks",
                func=self.analyze_email_blocks_tool,
                description="Analyze email blocks to extract restaurant staff contacts. Input should be the complete email blocks text from Search_Restaurant_Emails tool. Returns JSON array of contacts."
            )
        ]

if __name__ == "__main__":
    restaurants = [
        "CAVA"
    ]

    tools_helper = RestaurantContactTools(restaurants)

    s = tools_helper.search_and_extract_contacts("Poppy's")
    g = 1

