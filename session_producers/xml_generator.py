from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime

def build_delete_session_xml(uuid):
    root = Element("DeleteSession")
    SubElement(root, "ActionType").text = "DELETE"
    SubElement(root, "SessionUUID").text = uuid
    SubElement(root, "TimeOfAction").text = datetime.utcnow().isoformat()
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
    SubElement(root, "StartDateTime").text = data["start_datetime"].isoformat()
    SubElement(root, "EndDateTime").text = data["end_datetime"].isoformat()
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
        SubElement(root, "StartDateTime").text = changes["start_datetime"].isoformat()
    if "end_datetime" in changes:
        SubElement(root, "EndDateTime").text = changes["end_datetime"].isoformat()
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
