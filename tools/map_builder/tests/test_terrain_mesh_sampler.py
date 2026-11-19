import math
from types import SimpleNamespace

import pytest

from apps.launchers.terrain_mesh_sampler import TerrainMeshSampler, TerrainSource
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainState


def source(key,bounds,priority,height):
    return TerrainSource(key,bounds,129,129,priority,lambda:LocalTerrainState(
        LocalImageryState(key,'test',*bounds),129,129,tuple([height]*129**2),0,'source'))


class Index:
    def __init__(self,rows):self.rows=rows
    def point_sources(self,x,y):return [row for row in self.rows if row.contains(x,y)]


def sampler(rows):
    return TerrainMeshSampler(SimpleNamespace(state=SimpleNamespace(tiles=()),payloads=(),index=Index(rows)))


def test_parent_and_child_meshes_use_identical_heights_at_shared_points():
    bounds=tuple(map(math.radians,(-90,45,-87,49)))
    engine=sampler([source('coarse',tuple(map(math.radians,(-95,40,-80,55))),0,180),
                    source('detail',bounds,7,420)])
    z=10;x=int((-88.5+180)/360*2**(z+1));y=int((90-47)/180*2**z)
    parent=engine.mesh(z,x,y)['heights_m']
    child=engine.mesh(z+1,x*2,y*2)['heights_m']
    # Child NW quadrant: even child samples coincide with parent samples.
    for row in range(17):
        for col in range(17):
            assert child[(row*2)*33+col*2]==pytest.approx(parent[row*33+col])
    assert parent[16*33+16]==420


def test_height_field_has_no_drop_to_zero_when_detail_coverage_ends():
    engine=sampler([source('coarse',(-1,-1,1,1),0,180),source('detail',(-.1,-.1,.1,.1),7,420)])
    assert engine.value(0,0)==420
    assert engine.value(.1,0)==pytest.approx(180)
    assert engine.value(.10000001,0)==pytest.approx(180)
    assert len(engine.cache)<=32


def test_mesh_address_validation_and_empty_reference_plane():
    engine=sampler([])
    assert set(engine.mesh(0,0,0)['heights_m'])=={0}
    with pytest.raises(ValueError):engine.mesh(99,0,0)
