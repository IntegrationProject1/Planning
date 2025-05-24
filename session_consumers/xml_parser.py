import xml.etree.ElementTree as ET
from datetime import datetime

def _iso(s: str) -> datetime:
    # jouw formaat: 2025-06-15T13:00:00
    return datetime.fromisoformat(s)

def parse_create_session_xml(body: bytes) -> dict:
    root = ET.fromstring(body)
    data = {
        'session_uuid':       root.findtext('SessionUUID'),
        'event_uuid':         root.findtext('EventUUID'),
        'session_name':       root.findtext('SessionName'),
        'session_description': root.findtext('SessionDescription'),
        'start_datetime':     _iso(root.findtext('StartDateTime')),
        'end_datetime':       _iso(root.findtext('EndDateTime')),
        'session_location':   root.findtext('SessionLocation'),
        'session_type':       root.findtext('SessionType'),
        'capacity':           int(root.findtext('Capacity') or 0),
        'guest_speaker':      [],
        'registered_users':   []
    }

    # GuestSpeakers/GuestSpeaker/email
    gs = root.find('GuestSpeakers')
    if gs is not None:
        for speaker in gs.findall('GuestSpeaker'):
            email = speaker.findtext('email')
            if email:
                data['guest_speaker'].append(email)

    # RegisteredUsers/User/email (optioneel)
    ru = root.find('RegisteredUsers')
    if ru is not None:
        for user in ru.findall('User'):
            email = user.findtext('email')
            if email:
                data['registered_users'].append(email)

    return data

def parse_update_session_xml(body: bytes) -> dict:
    root = ET.fromstring(body)
    session_uuid = root.findtext('SessionUUID')
    changes = {}
    # vul changes dict indien aanwezig; voorbeeld:
    if root.find('SessionName') is not None:
        changes['session_name'] = root.findtext('SessionName')
    # herhaal voor andere velden...
    # Guests & RegisteredUsers net als create:
    gs = root.find('GuestSpeakers')
    if gs is not None:
        changes['guest_speaker'] = [g.findtext('email') for g in gs.findall('GuestSpeaker') if g.findtext('email')]
    ru = root.find('RegisteredUsers')
    if ru is not None:
        changes['registered_users'] = [u.findtext('email') for u in ru.findall('User') if u.findtext('email')]

    return {
        'session_uuid': session_uuid,
        'changes':      changes
    }

def parse_delete_session_xml(body: bytes) -> str:
    root = ET.fromstring(body)
    return root.findtext('SessionUUID')
