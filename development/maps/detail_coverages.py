"""Bounded Michigan detail pilots; imagery and elevation remain separate products."""
DETAIL_BOUNDS = {
    'detroit-midtown': (-83.085,42.315,-83.025,42.375),
    'auburn-hills': (-83.27,42.625,-83.195,42.695),
    'rochester': (-83.175,42.650,-83.110,42.705),
}
TERRAIN_DETAILS = {key+'-detail-10m':(key.replace('-',' ').title()+' 3DEP detail',bounds)
                   for key,bounds in DETAIL_BOUNDS.items()}
