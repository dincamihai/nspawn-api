import json
import pytest
from subprocess import PIPE
from mock import patch

import nspawn


@pytest.fixture
def app(request):
    nspawn.app.config['TESTING'] = True
    return nspawn.app.test_client()


def _make_patch(request, target):
    patcher = patch(target)
    request.addfinalizer(patcher.stop)
    return patcher.start()


@pytest.fixture
def mock_Popen(request):
    return _make_patch(request, 'nspawn.nspawn.Popen')


@pytest.fixture
def mock_uuid(request):
    return _make_patch(request, 'nspawn.nspawn.uuid')


def test_request(app, mock_Popen, mock_uuid):
    mock_Popen.return_value.communicate.return_value = ('', '')
    mock_Popen.return_value.returncode = 0
    mock_uuid.uuid4.return_value = 'new-container-id'
    resp = app.post('/boot', data={'machine': 'sles12sp2'})

    expected_cmd = ['machinectl', 'start', 'new-container-id']

    mock_Popen.assert_called_with(expected_cmd, stderr=PIPE, stdout=PIPE)

    assert json.loads(resp.data) == {
        'success': True, 'containerid': 'new-container-id'}
