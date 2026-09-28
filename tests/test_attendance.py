from datetime import date, timedelta, datetime
import pytest
from conftest import auth, token
from extensions import db
from models import Attendance, Employee, EmployeeLocation, utcnow

GPS = {"latitude": 22.57, "longitude": 88.36, "accuracy": 8}


@pytest.mark.parametrize('payload', [{}, {"latitude": 91, "longitude": 88, "accuracy": 8}, {"latitude": 22, "longitude": "bad", "accuracy": 8}, {"latitude": True, "longitude": 88, "accuracy": 8}, {"latitude": 22, "longitude": 88, "accuracy": -1}])
def test_attendance_requires_valid_gps(client, payload):
    headers = auth(token(client, 'exec1'))
    assert client.post('/api/attendance/check-in', json=payload, headers=headers).status_code == 422
    assert client.get('/api/attendance/me', headers=headers).get_json()['data'] == []


def test_gps_times_admin_visibility_and_isolation(client):
    headers = auth(token(client, 'exec1'))
    assert client.get('/api/attendance/today', headers=headers).get_json()['data']['record'] is None
    start = client.post('/api/attendance/check-in', json={**GPS, 'check_in': '1900-01-01'}, headers=headers).get_json()['data']
    assert start['check_in_lat'] == GPS['latitude']
    assert datetime.fromisoformat(start['check_in']).year != 1900
    assert datetime.fromisoformat(start['check_in']).tzinfo is not None
    assert client.get('/api/attendance/today', headers=headers).get_json()['data']['active']['id'] == start['id']
    assert client.post('/api/attendance/check-out', json={}, headers=headers).status_code == 422
    assert client.post('/api/attendance/check-in', json=GPS, headers=headers).status_code == 409
    end = client.post('/api/attendance/check-out', json=GPS, headers=headers).get_json()['data']
    assert end['id'] == start['id'] and end['check_out'] and not end['is_active']
    assert end['check_out_lng'] == GPS['longitude']
    assert client.post('/api/attendance/check-out', json=GPS, headers=headers).status_code == 409
    assert client.get('/api/attendance', headers=headers).status_code == 403
    assert client.get('/api/attendance/me', headers=auth(token(client, 'exec2'))).get_json()['data'] == []
    rows = client.get('/api/attendance', headers=auth(token(client, 'admin'))).get_json()['data']
    assert rows[0]['id'] == start['id'] and rows[0]['check_out'] and rows[0]['employee'] == 'Exec1'
    assert EmployeeLocation.query.count() == 2


def test_overnight_active_checkin_can_be_closed(client):
    employee = Employee.query.filter_by(employee_code='E1').one()
    db.session.add(Attendance(employee_id=employee.id, work_date=date.today()-timedelta(days=1), check_in=utcnow()-timedelta(hours=10)))
    db.session.commit()
    headers = auth(token(client, 'exec1'))
    assert client.post('/api/attendance/check-in', json=GPS, headers=headers).status_code == 409
    assert client.get('/api/attendance/today', headers=headers).get_json()['data']['active']
    assert client.post('/api/attendance/check-out', json=GPS, headers=headers).status_code == 200
    assert client.get('/api/attendance/today', headers=headers).get_json()['data']['active'] is None
    assert client.post('/api/attendance/check-in', json=GPS, headers=headers).status_code == 201
