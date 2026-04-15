import sys
import os
import os.path
import datetime
from icalendar import Calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scope required to read and write events to Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def authenticate_google_calendar():
    """Handles OAuth2 authentication and returns the Google Calendar service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}. Prompting for re-auth.")
                os.remove('token.json')
                return authenticate_google_calendar()
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: 'credentials.json' not found.")
                print("Please download your OAuth client ID from Google Cloud Console and save it as 'credentials.json' in this folder.")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Google Calendar service: {e}")
        sys.exit(1)

def format_datetime(dt):
    """Formats datetime objects for Google Calendar API format."""
    if hasattr(dt, 'dt'):
        dt = dt.dt

    if isinstance(dt, datetime.datetime):
        # If naive, assume local but format properly. Ideally ICS has TZ.
        return {'dateTime': dt.isoformat()}
    elif isinstance(dt, datetime.date):
        return {'date': dt.isoformat()}
    return None

def extract_reminders(component):
    """Extracts VALARM components and converts them to Google Calendar reminders."""
    alarms = component.walk('VALARM')
    if not alarms:
        return None

    overrides = []
    for alarm in alarms:
        trigger = alarm.get('TRIGGER')
        if trigger and hasattr(trigger, 'dt'):
            # trigger.dt is a timedelta object
            minutes_before = int(abs(trigger.dt.total_seconds()) // 60)
            # Google Calendar restricts max reminder time to 4 weeks (40320 minutes)
            if 0 <= minutes_before <= 40320:
                overrides.append({
                    'method': 'popup',
                    'minutes': minutes_before
                })
    
    if overrides:
        return {'useDefault': False, 'overrides': overrides}
    return None

def event_exists(service, calendar_id, summary, start_api_fmt):
    """Checks if an event with the exact same summary and start time already exists."""
    try:
        # Determine timeMin bound for querying
        time_min = start_api_fmt.get('dateTime') or (start_api_fmt.get('date') + 'T00:00:00Z')
        
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin=time_min,
            maxResults=10, # Check small window
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        for event in events:
            if event.get('summary') == summary:
                # Basic check to see if start times match
                e_start = event.get('start', {})
                if e_start.get('dateTime') == start_api_fmt.get('dateTime') or \
                   e_start.get('date') == start_api_fmt.get('date'):
                    return event
        return None
    except Exception as e:
        print(f"Warning: Could not perform duplicate check: {e}")
        return None

def process_ics(file_path, service):
    """Parses the ICS file and inserts events into Google Calendar."""
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    print(f"Reading {file_path}...")
    try:
        with open(file_path, 'rb') as f:
            cal = Calendar.from_ical(f.read())
    except Exception as e:
        print(f"ERROR parsing ICS file: {e}")
        sys.exit(1)

    calendar_id = 'primary'
    events = cal.walk('VEVENT')
    print(f"Found {len(events)} events. Starting import...\n")

    for idx, component in enumerate(events, 1):
        summary = str(component.get('SUMMARY', 'Untitled Event'))
        start_dt = component.get('DTSTART')
        end_dt = component.get('DTEND')

        if not start_dt:
            print(f"[{idx}/{len(events)}] Skipping '{summary}': Missing DTSTART.")
            continue

        start_api = format_datetime(start_dt)
        end_api = format_datetime(end_dt) if end_dt else start_api

        # Prepare Event Body
        event_body = {
            'summary': summary,
            'start': start_api,
            'end': end_api,
        }

        # Standard Fields
        description = component.get('DESCRIPTION')
        if description:
            event_body['description'] = str(description)

        location = component.get('LOCATION')
        if location:
            event_body['location'] = str(location)

        # Reminders
        reminders = extract_reminders(component)
        if reminders:
            event_body['reminders'] = reminders

        # Custom Fields
        color_id = component.get('X-COLOR-ID')
        if color_id:
            event_body['colorId'] = str(color_id)

        # Custom Metadata
        is_task = component.get('X-IS-TASK')
        is_shiftable = component.get('X-IS-SHIFTABLE')
        
        if is_task is not None or is_shiftable is not None:
            private_props = {}
            if is_task is not None:
                private_props['isTask'] = str(is_task).lower()
            if is_shiftable is not None:
                private_props['isShiftable'] = str(is_shiftable).lower()
                
            event_body['extendedProperties'] = {
                'private': private_props
            }

        # Check for duplicate
        existing_event = event_exists(service, calendar_id, summary, start_api)
        if existing_event:
            try:
                # Update existing event
                updated_event = service.events().update(
                    calendarId=calendar_id, 
                    eventId=existing_event['id'], 
                    body=event_body
                ).execute()
                print(f"[{idx}/{len(events)}] UPDATED existing event: {summary}")
            except HttpError as e:
                print(f"[{idx}/{len(events)}] ERROR updating '{summary}': {e}")
        else:
            try:
                # Insert new event
                created_event = service.events().insert(
                    calendarId=calendar_id, 
                    body=event_body
                ).execute()
                print(f"[{idx}/{len(events)}] CREATED event: {summary} ({created_event.get('htmlLink')})")
            except HttpError as e:
                print(f"[{idx}/{len(events)}] ERROR creating '{summary}': {e}")

    print("\nImport completed.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_calendar.py <path_to_ics_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    
    print("Authenticating with Google Calendar API...")
    service = authenticate_google_calendar()
    print("Authentication successful.\n")
    
    process_ics(file_path, service)

if __name__ == '__main__':
    main()