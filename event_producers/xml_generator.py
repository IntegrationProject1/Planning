import xml.etree.ElementTree as ET
from datetime import datetime, timezone

def format_datetime(value, timespec="microseconds") -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        return str(value or "")
    
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc).isoformat(timespec=timespec).replace('+00:00', 'Z')

def build_event_xml(data: dict) -> str:
    event = ET.Element("CreateEvent")

    ET.SubElement(event, "EventUUID").text = str(data.get("uuid", ""))

    ET.SubElement(event, "EventName").text = data.get("name", "")
    ET.SubElement(event, "EventDescription").text = data.get("description", "")

    ET.SubElement(event, "StartDateTime").text = format_datetime(data.get("start_datetime"), timespec="milliseconds")
    ET.SubElement(event, "EndDateTime").text   = format_datetime(data.get("end_datetime"), timespec="milliseconds")

    ET.SubElement(event, "EventLocation").text = data.get("location", "")
    ET.SubElement(event, "Organisator").text   = data.get("organizer", "")
    ET.SubElement(event, "Capacity").text      = str(data.get("capacity", 0))
    ET.SubElement(event, "EventType").text     = data.get("event_type", "")

    return ET.tostring(event, encoding="unicode")

def build_update_xml(uuid: str, changed_fields: dict) -> str:
    root = ET.Element("UpdateEvent")
    ET.SubElement(root, "EventUUID").text = uuid

    for name, new_value in changed_fields.items():
        if name == "RegisteredUsers" and isinstance(new_value, list):
            users_elem = ET.SubElement(root, "RegisteredUsers")
            for user in new_value:
                user_elem = ET.SubElement(users_elem, "User")
                ET.SubElement(user_elem, "UUID").text = user
        else:
            if isinstance(new_value, datetime):
                timespec = "milliseconds" if name in ["StartDateTime", "EndDateTime"] else "microseconds"
                value = format_datetime(new_value, timespec=timespec)
            else:
                value = str(new_value)
            ET.SubElement(root, name).text = value
            print(f"Update veld '{name}' met waarde: {value}", flush=True)

    return ET.tostring(root, encoding="unicode")

def build_delete_xml(uuid: str) -> str:
    root = ET.Element("DeleteEvent")
    
    ET.SubElement(root, "ActionType").text = "DELETE"
    ET.SubElement(root, "EventUUID").text = uuid

    time_of_action = format_datetime(datetime.utcnow(), timespec="microseconds")
    ET.SubElement(root, "TimeOfAction").text = time_of_action

    return ET.tostring(root, encoding="unicode")
