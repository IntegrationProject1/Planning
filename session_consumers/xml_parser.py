import xml.etree.ElementTree as ET
from dateutil import parser as dtparser

def _get_text(elem, tag, required=False):
    child = elem.find(tag)
    if child is None or child.text is None:
        if required:
            raise ValueError(f"Missing required element <{tag}>")
        return None
    return child.text.strip()

def _get_list_of_emails(parent, child_tag):
    emails = []
    if parent is None:
        return emails
    for c in parent.findall(child_tag):
        email = _get_text(c, 'email')
        if email:
            emails.append(email)
    return emails

def parse_create_session_xml(xml_str):
    root = ET.fromstring(xml_str)
    data = {
        'session_uuid':        dtparser.isoparse(_get_text(root, 'SessionUUID', True)),
        'event_uuid':          _get_text(root, 'EventUUID', True),
        'session_name':        _get_text(root, 'SessionName', True),
        'session_description': _get_text(root, 'SessionDescription'),
        'guest_speakers':      _get_list_of_emails(root.find('GuestSpeakers'), 'GuestSpeaker'),
        'capacity':            (lambda c: int(c) if c else None)(_get_text(root, 'Capacity')),
        'start_datetime':      (lambda s: dtparser.isoparse(s) if s else None)(_get_text(root, 'StartDateTime')),
        'end_datetime':        (lambda e: dtparser.isoparse(e) if e else None)(_get_text(root, 'EndDateTime')),
        'session_location':    _get_text(root, 'SessionLocation'),
        'session_type':        _get_text(root, 'SessionType'),
        'registered_users':    _get_list_of_emails(root.find('RegisteredUsers'), 'User'),
    }
    return data

def parse_update_session_xml(xml_str):
    root = ET.fromstring(xml_str)
    session_uuid = dtparser.isoparse(_get_text(root, 'SessionUUID', True))
    changes = {}
    for tag, key, caster in [
        ('SessionName','session_name',str),
        ('SessionDescription','session_description',str),
        ('Capacity','capacity',int),
        ('SessionLocation','session_location',str),
        ('SessionType','session_type',str),
    ]:
        txt = _get_text(root, tag)
        if txt is not None:
            changes[key] = caster(txt)
    for tag, key in [('StartDateTime','start_datetime'), ('EndDateTime','end_datetime')]:
        txt = _get_text(root, tag)
        if txt:
            changes[key] = dtparser.isoparse(txt)
    gs = root.find('GuestSpeakers')
    if gs is not None:
        changes['guest_speakers']   = _get_list_of_emails(gs, 'GuestSpeaker')
    ru = root.find('RegisteredUsers')
    if ru is not None:
        changes['registered_users'] = _get_list_of_emails(ru, 'User')
    return {'session_uuid': session_uuid, 'changes': changes}

def parse_delete_session_xml(xml_str):
    root = ET.fromstring(xml_str)
    return dtparser.isoparse(_get_text(root, 'SessionUUID', True))
