import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, List

def build_event_xml(data: Dict[str, Any]) -> str:
    """
    Bouwt een CreateEvent XML-payload volgens de XSD:
      - <CreateEvent>
          <EventUUID>…</EventUUID>
          <EventName>…</EventName>
          <EventDescription>…</EventDescription>
          <StartDateTime>…</StartDateTime>
          <EndDateTime>…</EndDateTime>
          <EventLocation>…</EventLocation>
          <Organisator>…</Organisator>
          <Capacity>…</Capacity>
          <EventType>…</EventType>
          <RegisteredUsers>  (optioneel)
            <User><UUID>…</UUID></User>*
          </RegisteredUsers>
      </CreateEvent>
    """
    event = ET.Element("CreateEvent")

    # EventUUID
    ev_uuid = data.get("uuid")
    if isinstance(ev_uuid, datetime):
        text_uuid = ev_uuid.isoformat() + "Z"
    else:
        text_uuid = str(ev_uuid or "")
    ET.SubElement(event, "EventUUID").text = text_uuid

    # Basisvelden
    ET.SubElement(event, "EventName").text        = data.get("name", "")
    ET.SubElement(event, "EventDescription").text = data.get("description", "")
    start = data.get("start_datetime")
    ET.SubElement(event, "StartDateTime").text    = (start.isoformat() + "Z") if isinstance(start, datetime) else str(start or "")
    end   = data.get("end_datetime")
    ET.SubElement(event, "EndDateTime").text      = (end.isoformat() + "Z")   if isinstance(end, datetime)   else str(end or "")
    ET.SubElement(event, "EventLocation").text    = data.get("location", "")
    ET.SubElement(event, "Organisator").text      = data.get("organisator", "") or data.get("organizer", "")
    ET.SubElement(event, "Capacity").text         = str(data.get("capacity", 0))
    ET.SubElement(event, "EventType").text        = data.get("event_type", "")

    # Optioneel: RegisteredUsers
    users: List[Dict[str, str]] = data.get("registered_users") or []
    if users:
        ru = ET.SubElement(event, "RegisteredUsers")
        for u in users:
            u_elem = ET.SubElement(ru, "User")
            ET.SubElement(u_elem, "UUID").text = str(u.get("uuid", ""))

    return ET.tostring(event, encoding="unicode")

def build_update_xml(event_uuid: datetime, changed_fields: Dict[str, Any]) -> str:
    """
    Bouwt een UpdateEvent XML-payload:
      - <UpdateEvent>
          <EventUUID>…</EventUUID>
          <!-- alleen de velden in changed_fields -->
          <EventName>…</EventName>?
          <EventDescription>…</EventDescription>?
          etc.
      </UpdateEvent>
    changed_fields verwacht keys als:
      "name","description","start_datetime","end_datetime",
      "location","organisator","capacity","event_type"
    Deze worden automatisch omgezet naar de juiste XML-tags.
    """
    root = ET.Element("UpdateEvent")

    # EventUUID
    if isinstance(event_uuid, datetime):
        ET.SubElement(root, "EventUUID").text = event_uuid.isoformat() + "Z"
    else:
        ET.SubElement(root, "EventUUID").text = str(event_uuid)

    # Map veldnaam -> XML-tag
    field_map = {
        "name":           "EventName",
        "description":    "EventDescription",
        "start_datetime": "StartDateTime",
        "end_datetime":   "EndDateTime",
        "location":       "EventLocation",
        "organisator":    "Organisator",
        "capacity":       "Capacity",
        "event_type":     "EventType"
    }

    for key, val in changed_fields.items():
        tag = field_map.get(key)
        if not tag:
            continue
        if isinstance(val, datetime):
            text = val.isoformat() + "Z"
        else:
            text = str(val)
        ET.SubElement(root, tag).text = text

    return ET.tostring(root, encoding="unicode")

def build_delete_xml(event_uuid: datetime) -> str:
    """
    Bouwt een DeleteEvent XML-payload:
      - <DeleteEvent>
          <EventUUID>…</EventUUID>
      </DeleteEvent>
    """
    root = ET.Element("DeleteEvent")
    if isinstance(event_uuid, datetime):
        ET.SubElement(root, "EventUUID").text = event_uuid.isoformat() + "Z"
    else:
        ET.SubElement(root, "EventUUID").text = str(event_uuid)
    return ET.tostring(root, encoding="unicode")
