import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

_field_map = {
    'EventUUID':       'uuid',
    'EventName':       'name',
    'EventDescription':'description',
    'StartDateTime':   'start_datetime',
    'EndDateTime':     'end_datetime',
    'EventLocation':   'location',
    'Organisator':     'organisator',
    'Capacity':        'capacity',
    'EventType':       'event_type'
}


def _parse_iso_dt(text: str) -> datetime:
    s = (text or '').strip()
    if s.endswith('Z'):
        s = s[:-1] + '+00:00'
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def parse_create_event_xml(xml_str: str) -> Dict[str, Any]:
    root = ET.fromstring(xml_str)
    if root.tag != 'CreateEvent':
        raise ValueError(f"Unexpected root '{root.tag}', expected CreateEvent")
    data: Dict[str, Any] = {}

    for elem in root:
        tag = elem.tag
        if tag in _field_map:
            key = _field_map[tag]
            txt = (elem.text or '').strip()
            if key == 'uuid':
                data[key] = txt
            elif key in ('start_datetime', 'end_datetime'):
                data[key] = _parse_iso_dt(txt)
            elif key == 'capacity':
                cap = int(txt or 0)
                if cap <= 0:
                    raise ValueError("Capacity must be positive")
                data[key] = cap
            else:
                data[key] = txt

    # handle RegisteredUsers on create
    users = root.find('RegisteredUsers')
    if users is not None:
        data['registered_users'] = [
            user.findtext('UUID').strip()
            for user in users.findall('User')
            if user.findtext('UUID')
        ]

    missing = [f for f in ('uuid','name','description','start_datetime','end_datetime',
                           'location','organisator','capacity','event_type')
               if f not in data]
    if missing:
        raise ValueError(f"Missing fields: {missing}")

    return data


def parse_update_event_xml(xml_str: str) -> Tuple[str, Dict[str, Any]]:
    root = ET.fromstring(xml_str)
    if root.tag != 'UpdateEvent':
        raise ValueError(f"Unexpected root '{root.tag}', expected UpdateEvent")

    raw = (root.findtext('EventUUID') or '').strip()
    if not raw:
        raise ValueError("Missing EventUUID")
    uuid = raw

    fields: Dict[str, Any] = {}
    for tag in ('EventName','EventDescription','StartDateTime','EndDateTime',
                'EventLocation','Organisator','Capacity','EventType'):
        txt = root.findtext(tag)
        if txt is not None and txt.strip() != '':
            key = _field_map[tag]
            if key in ('start_datetime','end_datetime'):
                fields[key] = _parse_iso_dt(txt.strip())
            elif key == 'capacity':
                val = int(txt.strip())
                if val <= 0:
                    raise ValueError("Capacity must be positive")
                fields[key] = val
            else:
                fields[key] = txt.strip()

    # handle RegisteredUsers on update
    users = root.find('RegisteredUsers')
    if users is not None:
        fields['registered_users'] = [
            user.findtext('UUID').strip()
            for user in users.findall('User')
            if user.findtext('UUID')
        ]

    return uuid, fields


def parse_delete_event_xml(xml_str: str) -> str:
    root = ET.fromstring(xml_str)
    if root.tag != 'DeleteEvent':
        raise ValueError(f"Unexpected root '{root.tag}', expected DeleteEvent")
    raw = (root.findtext('EventUUID') or '').strip()
    if not raw:
        raise ValueError("Missing EventUUID")
    return raw
