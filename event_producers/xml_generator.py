import xml.etree.ElementTree as ET
from datetime import datetime

def build_event_xml(data: dict) -> str:
    """
    Build a <CreateEvent> XML string from `data` dict.
    UUID, StartDateTime en EndDateTime krijgen altijd millisecond-precisie + 'Z'.
    """
    event = ET.Element("CreateEvent")

    # UUID (kan datetime of string zijn)
    uuid_val = data.get('uuid')
    if isinstance(uuid_val, datetime):
        uuid_txt = uuid_val.isoformat(timespec='milliseconds') + 'Z'
    else:
        uuid_txt = str(uuid_val or '')
    ET.SubElement(event, "UUID").text = uuid_txt

    ET.SubElement(event, "Name").text = data.get("name", "")
    ET.SubElement(event, "Description").text = data.get("description", "")

    # StartDateTime
    start_val = data.get("start_datetime")
    if isinstance(start_val, datetime):
        start_txt = start_val.isoformat(timespec='milliseconds') + 'Z'
    else:
        start_txt = str(start_val or "")
    ET.SubElement(event, "StartDateTime").text = start_txt

    # EndDateTime
    end_val = data.get("end_datetime")
    if isinstance(end_val, datetime):
        end_txt = end_val.isoformat(timespec='milliseconds') + 'Z'
    else:
        end_txt = str(end_val or "")
    ET.SubElement(event, "EndDateTime").text = end_txt

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
        if isinstance(new_value, datetime):
            value = new_value.isoformat(timespec='milliseconds') + 'Z'
        else:
            value = str(new_value)
        print(f"Update veld '{name}' met waarde: {value}", flush=True)
        ET.SubElement(field, "NewValue").text = value

    return ET.tostring(root, encoding="unicode")

def build_delete_xml(uuid: str) -> str:
    root = ET.Element("DeleteEvent")
    ET.SubElement(root, "UUID").text = uuid
    return ET.tostring(root, encoding="unicode")