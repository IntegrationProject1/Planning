from event_producers.xml_generator import build_event_xml, build_update_xml, build_delete_xml
from datetime import datetime, timezone

dummy_event = {
    'uuid': '1234',
    'calendar_id': 'abc',
    'name': 'Test Event',
    'created_at': datetime.now(timezone.utc),
    'start_datetime': datetime(2024, 5, 10, 10, 0),
    'end_datetime': datetime(2024, 5, 10, 12, 0),
    'description': 'Beschrijving',
    'capacity': 10,
    'organizer': 'Organisator',
    'event_type': 'Workshop',
    'location': 'Lokaal 1',
    'last_fetched': datetime.now(timezone.utc)
}

def test_build_event_xml():
    xml = build_event_xml(dummy_event)
    assert "<Event>" in xml
    assert "<UUID>1234</UUID>" in xml
    assert "<Capacity>10</Capacity>" in xml

def test_build_update_xml():
    xml = build_update_xml("1234", {'capacity': 20})
    assert "<UpdateEvent>" in xml
    assert "<UUID>1234</UUID>" in xml
    assert "<Name>capacity</Name>" in xml
    assert "<NewValue>20</NewValue>" in xml

def test_build_delete_xml():
    xml = build_delete_xml("1234")
    assert "<DeleteEvent>" in xml
    assert "<UUID>1234</UUID>" in xml
