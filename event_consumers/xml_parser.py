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


def _parse_iso_dt(text: str) -> datetime:
    txt = (text or '').strip()
    if txt.endswith('Z'):
        txt = txt[:-1]
    return datetime.fromisoformat(txt)


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
            # Parse datetime-like fields (uuid, start, end)
            if key in ('uuid', 'start_datetime', 'end_datetime'):
                data[key] = _parse_iso_dt(text)
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
            uid = (user.findtext('UUID') or '').strip()
            if uid:
                users.append(uid)
        data['registered_users'] = users

    missing = [f for f in ('uuid', 'name', 'start_datetime', 'end_datetime',
                       'location', 'organizer', 'capacity', 'event_type') if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    return data


def parse_update_event_xml(xml_str: str) -> Tuple[datetime, Dict[str, Any]]:
    root = ET.fromstring(xml_str)
    if root.tag not in ('UpdateEvent', 'EventUpdate'):
        raise ValueError(f"Unexpected root element '{root.tag}', expected UpdateEvent or EventUpdate")
    raw_uuid = (root.findtext('UUID') or '').strip()
    if not raw_uuid:
        raise ValueError("Missing UUID in UpdateEvent")
    uuid = _parse_iso_dt(raw_uuid)

    fields: Dict[str, Any] = {}
    updates = root.find('FieldsToUpdate')
    if updates is not None:
        for field_elem in updates.findall('Field'):
            name = (field_elem.findtext('Name') or '').strip()
            new_value = (field_elem.findtext('NewValue') or '').strip()
            key = _field_map.get(name)
            if not key:
                continue
            if key in ('start_datetime', 'end_datetime'):
                fields[key] = _parse_iso_dt(new_value)
            elif key == 'capacity':
                val = int(new_value)
                if val <= 0:
                    raise ValueError("Capacity must be a positive integer according to XSD")
                fields[key] = val
            else:
                fields[key] = new_value

    return uuid, fields


def parse_delete_event_xml(xml_str: str) -> datetime:
    root = ET.fromstring(xml_str)
    if root.tag not in ('DeleteEvent', 'EventDelete'):
        raise ValueError(f"Unexpected root element '{root.tag}', expected DeleteEvent or EventDelete")
    raw_uuid = (root.findtext('UUID') or '').strip()
    if not raw_uuid:
        raise ValueError("Missing UUID in DeleteEvent")
    return _parse_iso_dt(raw_uuid)
