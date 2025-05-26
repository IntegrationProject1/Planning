from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime, timezone

def format_dt(dt, precision="milliseconds"):
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec=precision).replace("+00:00", "Z")

def build_delete_session_xml(uuid):
    root = Element("DeleteSession")
    SubElement(root, "ActionType").text = "DELETE"
    SubElement(root, "SessionUUID").text = uuid
    SubElement(root, "TimeOfAction").text = format_dt(datetime.utcnow(), "microseconds")
    return tostring(root, encoding="unicode")

def build_create_session_xml(data):
    root = Element("CreateSession")
    SubElement(root, "SessionUUID").text = data["uuid"]
    SubElement(root, "EventUUID").text = data["event_uuid"]
    SubElement(root, "SessionName").text = data.get("name", "")
    SubElement(root, "SessionDescription").text = data.get("description", "")

    speakers = SubElement(root, "GuestSpeakers")
    if data.get("guest_speaker"):
        speaker = SubElement(speakers, "GuestSpeaker")
        SubElement(speaker, "email").text = data["guest_speaker"]

    SubElement(root, "Capacity").text = str(data.get("capacity", 0))
    SubElement(root, "StartDateTime").text = format_dt(data.get("start_datetime"))
    SubElement(root, "EndDateTime").text = format_dt(data.get("end_datetime"))
    SubElement(root, "SessionLocation").text = data.get("location", "")
    SubElement(root, "SessionType").text = data.get("event_type", "")

    users = SubElement(root, "RegisteredUsers")
    for email in data.get("registered_users", []):
        user = SubElement(users, "User")
        SubElement(user, "email").text = email

    return tostring(root, encoding="unicode")

def build_update_session_xml(uuid, changes, registered_users):
    root = Element("UpdateSession")
    SubElement(root, "SessionUUID").text = uuid
    SubElement(root, "EventUUID").text = changes.get("event_uuid", "")
    SubElement(root, "SessionName").text = changes.get("name", "")
    SubElement(root, "SessionDescription").text = changes.get("description", "")

    speakers = SubElement(root, "GuestSpeakers")
    if "guest_speaker" in changes and changes["guest_speaker"]:
        speaker = SubElement(speakers, "GuestSpeaker")
        SubElement(speaker, "email").text = changes["guest_speaker"]

    if "capacity" in changes:
        SubElement(root, "Capacity").text = str(changes["capacity"])
    if "start_datetime" in changes:
        SubElement(root, "StartDateTime").text = format_dt(changes["start_datetime"])
    if "end_datetime" in changes:
        SubElement(root, "EndDateTime").text = format_dt(changes["end_datetime"])
    if "location" in changes:
        SubElement(root, "SessionLocation").text = changes["location"]
    if "event_type" in changes:
        SubElement(root, "SessionType").text = changes["event_type"]

    if registered_users:
        users = SubElement(root, "RegisteredUsers")
        for email in registered_users:
            user = SubElement(users, "User")
            SubElement(user, "email").text = email

    return tostring(root, encoding="unicode")
