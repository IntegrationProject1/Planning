import pytest
from datetime import datetime
from event_consumers.xml_parser import (
    parse_create_event_xml,
    parse_update_event_xml,
    parse_delete_event_xml
)

CREATE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<CreateEvent>
  <UUID>2025-08-15T10:00:00Z</UUID>
  <Name>TestEvent</Name>
  <Description>Desc</Description>
  <StartDateTime>2025-08-16T10:00:00Z</StartDateTime>
  <EndDateTime>2025-08-16T12:00:00Z</EndDateTime>
  <Location>Hall</Location>
  <Organisator>organizer@example.com</Organisator>
  <Capacity>50</Capacity>
  <EventType>Seminar</EventType>
  <RegisteredUsers>
    <User><UUID>user1@example.com</UUID></User>
    <User><UUID>user2@example.com</UUID></User>
  </RegisteredUsers>
</CreateEvent>'''

UPDATE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<UpdateEvent>
  <UUID>2025-08-15T10:00:00Z</UUID>
  <FieldsToUpdate>
    <Field>
      <Name>Description</Name>
      <NewValue>NewDesc</NewValue>
    </Field>
    <Field>
      <Name>Capacity</Name>
      <NewValue>75</NewValue>
    </Field>
  </FieldsToUpdate>
</UpdateEvent>'''

DELETE_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<DeleteEvent>
  <UUID>2025-08-15T10:00:00Z</UUID>
</DeleteEvent>'''


def test_parse_create_event_xml():
    data = parse_create_event_xml(CREATE_XML)
    assert isinstance(data['uuid'], datetime)
    assert data['name'] == 'TestEvent'
    assert data['capacity'] == 50
    assert len(data['registered_users']) == 2


def test_parse_update_event_xml():
    uid, fields = parse_update_event_xml(UPDATE_XML)
    assert isinstance(uid, datetime)
    assert fields['description'] == 'NewDesc'
    assert fields['capacity'] == 75


def test_parse_delete_event_xml():
    uid = parse_delete_event_xml(DELETE_XML)
    assert isinstance(uid, datetime)