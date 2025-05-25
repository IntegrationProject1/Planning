import xml.etree.ElementTree as ET
from datetime import datetime, timezone

def format_microseconds(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def format_milliseconds(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def build_event_xml(data: dict) -> str:
    event = ET.Element("CreateEvent")

    event_uuid = data.get('uuid')
    ET.SubElement(event, "EventUUID").text = (
        format_microseconds(event_uuid) if isinstance(event_uuid, datetime) else str(event_uuid or "")
    )

    ET.SubElement(event, "EventName").text        = data.get("name", "")
    ET.SubElement(event, "EventDescription").text = data.get("description", "")

    start_datetime = data.get("start_datetime")
    ET.SubElement(event, "StartDateTime").text = (
        format_milliseconds(start_datetime) if isinstance(start_datetime, datetime) else str(start_datetime or "")
    )

    end_datetime = data.get("end_datetime")
    ET.SubElement(event, "EndDateTime").text = (
        format_milliseconds(end_datetime) if isinstance(end_datetime, datetime) else str(end_datetime or "")
    )

    ET.SubElement(event, "EventLocation").text = data.get("location", "")
    ET.SubElement(event, "Organisator").text   = data.get("organizer", "")
    ET.SubElement(event, "Capacity").text      = str(data.get("capacity", 0))
    ET.SubElement(event, "EventType").text     = data.get("event_type", "")

    return ET.tostring(event, encoding="unicode")

def build_update_xml(event_datetime: datetime, changed_fields: dict) -> str:
    root = ET.Element("UpdateEvent")
    ET.SubElement(root, "EventUUID").text = format_microseconds(event_datetime)

    for name, new_value in changed_fields.items():
        if name == "RegisteredUsers" and isinstance(new_value, list):
            users_elem = ET.SubElement(root, "RegisteredUsers")
            for user in new_value:
                user_elem = ET.SubElement(users_elem, "User")
                ET.SubElement(user_elem, "UUID").text = user
        else:
            if isinstance(new_value, datetime):
                if name in ["StartDateTime", "EndDateTime"]:
                    value = format_milliseconds(new_value)
                else:
                    value = format_microseconds(new_value)
            else:
                value = str(new_value)
            ET.SubElement(root, name).text = value
            print(f"Update veld '{name}' met waarde: {value}", flush=True)

    return ET.tostring(root, encoding="unicode")

def build_delete_xml(uuid: str) -> str:
    root = ET.Element("DeleteEvent")
    ET.SubElement(root, "EventUUID").text = uuid

    time_of_action = format_microseconds(datetime.utcnow())
    ET.SubElement(root, "TimeOfAction").text = time_of_action

    return ET.tostring(root, encoding="unicode")
