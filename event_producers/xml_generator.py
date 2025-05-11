import xml.etree.ElementTree as ET
from datetime import datetime

def build_event_xml(data: dict) -> str:
    event = ET.Element("Event")

    ET.SubElement(event, "UUID").text = data['uuid']
    ET.SubElement(event, "Name").text = data.get("name", "")
    ET.SubElement(event, "Description").text = data.get("description", "")
    start_datetime = data.get("start_datetime")
    ET.SubElement(event, "StartDateTime").text = start_datetime.isoformat() if isinstance(start_datetime, datetime) else str(start_datetime or "")
    end_datetime = data.get("end_datetime")
    ET.SubElement(event, "EndDateTime").text = end_datetime.isoformat() if isinstance(end_datetime, datetime) else str(end_datetime or "")
    ET.SubElement(event, "Location").text = data.get("location", "")
    ET.SubElement(event, "Organisator").text = data.get("organizer", "")
    ET.SubElement(event, "Capacity").text = str(data.get("capacity", 0))
    ET.SubElement(event, "EventType").text = data.get("event_type", "")

    return ET.tostring(event, encoding="unicode")

def build_update_xml(uuid: str, changed_fields: dict) -> str:
    root = ET.Element("UpdateEvent")
    ET.SubElement(root, "UUID").text = uuid

    fields_to_update = ET.SubElement(root, "FieldsToUpdate")
    for name, new_value in changed_fields.items():
        field = ET.SubElement(fields_to_update, "Field")
        ET.SubElement(field, "Name").text = name
        value = new_value.isoformat() if isinstance(new_value, datetime) else str(new_value)
        print(f"Update veld '{name}' met waarde: {value}", flush=True)
        ET.SubElement(field, "NewValue").text = value

    return ET.tostring(root, encoding="unicode")

def build_delete_xml(uuid: str) -> str:
    root = ET.Element("DeleteEvent")
    ET.SubElement(root, "UUID").text = uuid
    return ET.tostring(root, encoding="unicode")