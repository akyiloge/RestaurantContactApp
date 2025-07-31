# app.py

import os
from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests

from gmail_service import GmailService

from dotenv import load_dotenv

from restaurant_contact_agent import RestaurantContactAgent

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-for-dev")

# Google OAuth
CLIENT_SECRETS_FILE = 'client_secret_web.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


@app.route('/')
def index():
    if 'credentials' not in session:
        return render_template('index.html', logged_in=False)
    return render_template('index.html', logged_in=True)


@app.route('/login')
def login():
    # Google OAuth flow
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['state'] = state
    return redirect(authorization_url)


@app.route('/callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/run-search', methods=['POST'])
def run_search():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data or 'restaurants' not in data:
        return jsonify({'error': 'Restaurant list is missing'}), 400

    restaurant_list = [name.strip() for name in data['restaurants'].split('\n') if name.strip()]

    # gmail_service = GmailService(session['credentials'])
    #
    # restaurant_name = "Mangia"
    # queries = [
    #     f'"{restaurant_name}"',
    #     f'from:@{restaurant_name.lower().replace(" ", "").replace("&", "")}',
    #     f'{restaurant_name.lower().replace(" ", "+")}',
    # ]
    #
    # res = gmail_service.search_emails(query=restaurant_name)
    # d = 3

    try:
        agent = RestaurantContactAgent(restaurant_list, session['credentials'])
        contacts = agent.run_contact_search()

        return jsonify(contacts)

    except Exception as e:
        print(f"Error during agent run: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)