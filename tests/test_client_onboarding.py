import io
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import pytest
from conftest import auth, token
from extensions import db
from models import Client, Photo, ClientOnboardingRequest


def camera_photo():
    buffer = io.BytesIO()
    Image.new('RGB', (32, 32), (30, 100, 200)).save(buffer, 'JPEG')
    buffer.seek(0)
    return buffer


def payload(**changes):
    values = dict(submission_id='a'*32, business_name='Test client', contact_person='Test contact',
                  mobile='9876543210', address='Test address', pin_code='700016',
                  latitude='22.57', longitude='88.36', accuracy='8', photo=(camera_photo(), '../../camera.jpg'))
    values.update(changes)
    return values


@pytest.fixture(autouse=True)
def upload_folder(app, tmp_path):
    app.config['UPLOAD_FOLDER'] = str(tmp_path)


def test_onboard_atomic_retry_and_admin_photo(client, app):
    executive = auth(token(client, 'exec1'))
    result = client.post('/api/clients/onboard', data=payload(), headers=executive)
    assert result.status_code == 201
    row = result.get_json()['data']
    assert row['pin_code'] == '700016' and row['latitude'] == 22.57
    assert len(row['photos']) == 1
    photo_id = row['photos'][0]['id']
    retry = client.post('/api/clients/onboard', data=payload(), headers=executive)
    assert retry.status_code == 200 and retry.get_json()['data']['id'] == row['id']
    assert Client.query.count() == Photo.query.count() == ClientOnboardingRequest.query.count() == 1
    assert len(list(Path(app.config['UPLOAD_FOLDER']).iterdir())) == 1
    assert client.post('/api/clients/onboard', data=payload(business_name='Changed'), headers=executive).status_code == 409
    assert client.get(f'/api/photos/{photo_id}/file').status_code == 401
    assert client.get(f'/api/photos/{photo_id}/file', headers=auth(token(client, 'exec2'))).status_code == 403
    photo = client.get(f'/api/photos/{photo_id}/file', headers=executive)
    assert photo.status_code == 200 and photo.mimetype == 'image/jpeg'
    assert Image.open(io.BytesIO(photo.data)).size == (32, 32)
    assert client.get(f"/api/clients/{row['id']}", headers=auth(token(client, 'admin'))).get_json()['data']['photos']
    assert client.post('/admin/login', data={'username': 'admin', 'password': 'Demo@123'}).status_code == 302
    assert b'Test client' in client.get(f"/admin/clients/{row['id']}").data
    assert client.get(f'/admin/photos/{photo_id}').status_code == 200


@pytest.mark.parametrize('change', [dict(business_name=' '), dict(mobile='123'), dict(pin_code=''), dict(pin_code='000000'), dict(latitude='nan'), dict(longitude='181')])
def test_onboard_validation_does_not_create_rows(client, app, change):
    response = client.post('/api/clients/onboard', data=payload(**change), headers=auth(token(client, 'exec1')))
    assert response.status_code == 422
    assert Client.query.count() == Photo.query.count() == 0
    assert not list(Path(app.config['UPLOAD_FOLDER']).iterdir())


def test_fake_image_is_rejected(client):
    response = client.post('/api/clients/onboard', data=payload(photo=(io.BytesIO(b'<script>bad</script>'), 'photo.jpg')), headers=auth(token(client, 'exec1')))
    assert response.status_code == 415
    assert Client.query.count() == 0


def test_commit_failure_rolls_back_and_removes_file(client, app):
    headers = auth(token(client, 'exec1'))
    with patch.object(db.session, 'commit', side_effect=RuntimeError('database unavailable')):
        with pytest.raises(RuntimeError):
            client.post('/api/clients/onboard', data=payload(), headers=headers)
    assert Client.query.count() == Photo.query.count() == 0
    assert not list(Path(app.config['UPLOAD_FOLDER']).iterdir())
