"""Map artifact identities change only with reviewed build inputs."""

import pytest

from development.maps.artifact_identity import (build_fingerprint, build_profile,
                                                 build_revision, validate_descriptor)


def test_artifact_fingerprints_are_kind_and_coverage_specific():
    overview = build_fingerprint('imagery', 'michigan-overview')
    assert len(overview) == 64
    assert overview == build_fingerprint('imagery', 'michigan-overview')
    assert overview != build_fingerprint('terrain', 'michigan-overview')
    assert overview != build_fingerprint('imagery', 'metro-detroit')
    assert 'nodata24' in build_revision('imagery')
    assert build_profile('imagery','michigan-overview') == '8192x8192'
    assert build_profile('imagery','metro-detroit') == '4096x4096-detail'


def test_artifact_identity_rejects_unknown_or_unnormalized_inputs():
    with pytest.raises(ValueError, match='kind'):
        build_fingerprint('roads', 'metro-detroit')
    with pytest.raises(ValueError, match='Coverage'):
        build_fingerprint('imagery', 'metro detroit')


def test_release_descriptor_must_match_current_build_inputs(tmp_path):
    descriptor = tmp_path/'imagery.zip.json'
    descriptor.write_text(__import__('json').dumps({
        'schema':1, 'kind':'imagery', 'coverage':'metro-detroit',
        'archive':'metro-detroit-imagery.zip', 'bytes':123, 'sha256':'a'*64,
        'build_profile':build_profile('imagery','metro-detroit'),
        'build_revision':build_revision('imagery'),
        'build_fingerprint':build_fingerprint('imagery','metro-detroit')}))
    assert validate_descriptor(descriptor,'imagery','metro-detroit')['schema'] == 1
    document = __import__('json').loads(descriptor.read_text())
    document['build_fingerprint'] = 'stale'
    descriptor.write_text(__import__('json').dumps(document))
    with pytest.raises(ValueError, match='does not match'):
        validate_descriptor(descriptor,'imagery','metro-detroit')
