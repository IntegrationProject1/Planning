from event_producers.xml_generator import build_event_xml, build_update_xml, build_delete_xml
from datetime import datetime

dummy_event = {
    'uuid': '2025-05-25T19:34:13.483000Z',
    'calendar_id': 'abc',
    'name': 'Test Event',
    'created_at': datetime.utcnow(),
    'start_datetime': datetime(2024, 5, 10, 10, 0),
    'end_datetime': datetime(2024, 5, 10, 12, 0),
    'description': 'Beschrijving',
    'capacity': 10,
    'organizer': 'Organisator',
    'event_type': 'Workshop',
    'location': 'Lokaal 1',
    'last_fetched': datetime.utcnow()
}

def test_build_event_xml():
    xml = build_event_xml(dummy_event)
    assert "<CreateEvent>" in xml
    assert "<EventUUID>" in xml
    assert "<EventName>Test Event</EventName>" in xml
    assert "<Capacity>10</Capacity>" in xml
    assert "<Organisator>Organisator</Organisator>" in xml

def test_build_update_xml():
    event_uuid = dummy_event["uuid"]
    xml = build_update_xml(event_uuid, {"Capacity": 20})
    assert "<UpdateEvent>" in xml
    assert "<EventUUID>" in xml
    assert "<Capacity>20</Capacity>" in xml
    assert "<Name>" not in xml 

def test_build_delete_xml():
    xml = build_delete_xml("1234") 
    assert "<DeleteEvent>" in xml
    assert "<EventUUID>1234</EventUUID>" in xml
