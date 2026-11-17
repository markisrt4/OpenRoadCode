import json

from development.maps.resume_statewide_detail import resume
from development.maps.statewide_detail_plan import PROFILE


def fixture(tmp_path):
    cell = dict(id='mi-z10-268-376', bounds_deg=[1, 2, 3, 4])
    plan = dict(cells=[cell], batches=[dict(id='70', cells=[cell])])
    directory = tmp_path/'mi-detail-reports-70-123'
    directory.mkdir()
    descriptor = dict(coverage=cell['id'], bounds_deg=cell['bounds_deg'],
                      profile=PROFILE, sha256='a'*64, bytes=10)
    (directory/'cell.zip.json').write_text(json.dumps(descriptor))
    return plan


def test_completed_artifact_is_referenced_without_copying(tmp_path):
    plan = fixture(tmp_path)
    result = resume(plan, tmp_path, {('123', 'mi-detail-batch-70-123')})
    assert result['missing_batches'] == []
    assert result['cells']['mi-z10-268-376']['run_id'] == '123'


def test_missing_or_expired_artifact_is_rebuilt(tmp_path):
    plan = fixture(tmp_path)
    assert resume(plan, tmp_path, set())['missing_batches'] == ['70']


def test_reference_survives_another_resume_generation(tmp_path):
    plan = fixture(tmp_path)
    live = {('123', 'mi-detail-batch-70-123')}
    first = resume(plan, tmp_path, live)
    empty = tmp_path/'empty'
    empty.mkdir()
    second = resume(plan, empty, live, first)
    assert second['cells'] == first['cells']
    assert not second['missing_batches']
