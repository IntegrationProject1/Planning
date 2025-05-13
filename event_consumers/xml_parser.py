import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List, Tuple

_field_map = {
    'UUID': 'uuid',
    'Name': 'name',
    'Description': 'description',
    'StartDateTime': 'start_datetime',
    'EndDateTime': 'end_datetime',
    'Location': 'location',
    'Organisator': 'organizer',
    'Capacity': 'capacity',
    'EventType': 'event_type'
}

def parse_create_event_xml(xml_str: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_str)
    if root.tag not in ('CreateEvent', 'Event'):
        raise ValueError(f"Unexpected root element '{root.tag}', expected CreateEvent or Event")
    data: Dict[str, Any] = {}
    for elem in root:
        tag = elem.tag
        if tag in _field_map:
            key = _field_map[tag]
            text = (elem.text or '').strip()
            if key in ('start_datetime', 'end_datetime'):
                data[key] = datetime.fromisoformat(text)
            elif key == 'capacity':
                cap = int(text or 0)
                if cap <= 0:
                    raise ValueError("Capacity must be a positive integer according to XSD")
                data[key] = cap
            else:
                data[key] = text
    users_elem = root.find('RegisteredUsers')
    if users_elem is not None:
        users: List[str] = []
        for user in users_elem.findall('User'):
            uid = user.findtext('UUID')
            if uid:
                users.append(uid)
        data['registered_users'] = users
    missing = [f for f in ('uuid','name','start_datetime','end_datetime','location','organizer','capacity','event_type') if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    return data

def parse_update_event_xml(xml_str: str) -> Tuple[str, Dict[str, Any]]:
    root = ET.fromstring(xml_str)
    if root.tag not in ('UpdateEvent', 'EventUpdate'):
        raise ValueError(f"Unexpected root element '{root.tag}', expected UpdateEvent or EventUpdate")
    uuid = root.findtext('UUID')
    fields: Dict[str, Any] = {}
    updates = root.find('FieldsToUpdate')
    if updates is not None:
        for field_elem in updates.findall('Field'):
            name = field_elem.findtext('Name')
            new_value = field_elem.findtext('NewValue')
            if not name or new_value is None:
                continue
            key = _field_map.get(name)
            if not key:
                continue
            text = new_value.strip()
            if key in ('start_datetime', 'end_datetime'):
                fields[key] = datetime.fromisoformat(text)
            elif key == 'capacity':
                val = int(text)
                if val <= 0:
                    raise ValueError("Capacity must be a positive integer according to XSD")
                fields[key] = val
            else:
                fields[key] = text
    return uuid, fields

def parse_delete_event_xml(xml_str: str) -> str:
    root = ET.fromstring(xml_str)
    if root.tag not in ('DeleteEvent', 'EventDelete'):
        raise ValueError(f"Unexpected root element '{root.tag}', expected DeleteEvent or EventDelete")
    uuid = root.findtext('UUID')
    if not uuid:
        raise ValueError("Missing UUID in DeleteEvent")
    return uuid
