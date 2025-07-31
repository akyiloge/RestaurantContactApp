import os
import base64
import json
import pickle
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from typing import Dict, List


class GmailService:

    # __init__
    def __init__(self, credentials_info: Dict):
        creds = Credentials.from_authorized_user_info(credentials_info,
                                                      ['https://www.googleapis.com/auth/gmail.readonly'])
        self.service = build('gmail', 'v1', credentials=creds)

    # def __init__(self):
    #     self.service = None
    #     self.setup_gmail_service()

    # This code block is required for local
    def setup_gmail_service(self):
        """Gmail API setup - OAuth2 authentication"""
        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        creds = None

        if os.path.exists('gmail_token.pickle'):
            with open('gmail_token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(  # Flow -> InstalledAppFlow
                    'gmail_credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('gmail_token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)



    def search_emails(self, query: str, max_results: int = 50) -> List[Dict]:
        """Search emails in Gmail"""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_data = []

            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='full'
                ).execute()

                email_data.append(self.parse_email(msg))

            return email_data

        except Exception as e:
            print(f"Gmail searach error: {e}")
            return []



    def parse_email(self, message: Dict) -> Dict:
        """Parse Email message"""
        payload = message['payload']
        headers = payload.get('headers', [])

        email_data = {
            'message_id': message['id'],
            'subject': '',
            'from': '',
            'to': '',
            'date': '',
            'body': '',
            'thread_id': message['threadId']
        }

        for header in headers:
            name = header['name'].lower()
            if name == 'subject':
                email_data['subject'] = header['value']
            elif name == 'from':
                email_data['from'] = header['value']
            elif name == 'to':
                email_data['to'] = header['value']
            elif name == 'date':
                email_data['date'] = header['value']

        # Email body'sini al
        email_data['body'] = self.extract_email_body(payload)

        return email_data



    def extract_email_body(self, payload: Dict) -> str:
        """Extract Email body"""
        body = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body += base64.urlsafe_b64decode(
                            part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    if 'data' in part['body']:
                        html_content = base64.urlsafe_b64decode(
                            part['body']['data']).decode('utf-8')
                        # HTML'den text çıkar (basit yöntem)
                        body += re.sub(r'<[^>]+>', '', html_content)
        else:
            if payload['body'].get('data'):
                body = base64.urlsafe_b64decode(
                    payload['body']['data']).decode('utf-8')

        return body