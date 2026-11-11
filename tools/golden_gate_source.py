"""Combine the immutable v3 source with bounded western terrain and vectors."""

from collections import Counter
import gzip
import json
import math

import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import map_coordinates
from shapely import make_valid
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import polygonize, transform, unary_union
from shapely.strtree import STRtree

from atlas_geometry import ORIGIN_UTM, camera_point, ground_point
from bay_overview import earth_geometry, regional_dem
from corridor_inputs import ROOT, TO_GEO, local_xy, sha
from corridor_source import HEIGHT_CLASSES, lines, number, polygons, rings
from golden_gate_geometry import ATLAS, WEST_ART, BRIDGE_FRAME, jump_points
from golden_gate_inputs import CACHE, EXTENT
from render_corridor import good_polygon, load_data

OUTPUT = ROOT/'data/golden-gate'
SOURCE = OUTPUT/'source.json.gz'
ROI = box(*EXTENT)


def covered(geom, high=95):
    x0,n0,x1,n1=geom.bounds
    xy=[camera_point((x,n,z)) for x in (x0,x1) for n in (n0,n1) for z in (0,high)]
    xx,yy,_=zip(*xy)
    return any(max(xx)>=f.x and min(xx)<=f.right and max(yy)>=f.y and min(yy)<=f.bottom
               for f in (*WEST_ART,BRIDGE_FRAME))


def terrain(old):
    corners=[ground_point(x,y,220) for x in (ATLAS.x,ATLAS.right) for y in (ATLAS.y,ATLAS.bottom)]
    xx,nn=zip(*corners)
    x=np.arange(math.floor(min(xx)-620),math.ceil(max(xx)+300),15.,dtype='float64')
    n=np.arange(math.floor(min(nn)-720),math.ceil(max(nn)+400),15.,dtype='float64')
    egrid,ngrid=np.meshgrid(x,n)
    east=old['terrain']
    interp=RegularGridInterpolator((east['n'],east['x']),east['z'],bounds_error=False,fill_value=np.nan)
    legacy=interp(np.stack((ngrid,egrid),axis=-1))
    # The regional DEM gives context in corners outside either detailed source.
    def sample(path):
        with rasterio.open(path) as ds:
            if ds.crs.to_epsg()!=32610:
                raise ValueError('Unexpected elevation CRS')
            dem=ds.read(1,masked=True).filled(np.nan)
            aff=~ds.transform
            rows=aff.e*(ngrid+ORIGIN_UTM[1])+aff.f-.5
            cols=aff.a*(egrid+ORIGIN_UTM[0])+aff.c-.5
            return map_coordinates(dem,[rows,cols],order=1,mode='constant',cval=np.nan)
    regional=sample(regional_dem()[0])
    west=sample(CACHE/'terrain.tif')
    western=np.where(np.isfinite(west),west,regional)
    mix=np.clip((egrid+3220)/950,0,1)
    z=np.where(np.isfinite(legacy), np.where(np.isfinite(west),western*(1-mix)+legacy*mix,legacy),western)
    z=np.nan_to_num(z,nan=2.6).clip(-1.5,360)
    elev=RegularGridInterpolator((n,x),z,bounds_error=False,fill_value=2.6)
    return {'x':x.tolist(),'n':n.tolist(),'z':np.round(z,2).tolist()}, elev


def polygon_land(coasts):
    """OSM coastline points have land on the left; retain small islands too."""
    pieces=list(polygonize(unary_union([ROI.boundary,*coasts])))
    if len(pieces)<3:
        raise ValueError(f'Western coastline only created {len(pieces)} polygons')
    index=STRtree(pieces)
    vote=Counter()
    for coast in coasts:
        for a,b in zip(coast.coords, list(coast.coords)[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            length=math.hypot(dx,dy)
            if length<3:
                continue
            x,y=(a[0]+b[0])/2,(a[1]+b[1])/2
            for sign in (-1,1):
                p=Point(x-sign*dy/length*1.3,y+sign*dx/length*1.3)
                for i in index.query(p,predicate='within'):
                    vote[i]+=length*sign
    land=unary_union([p for i,p in enumerate(pieces) if vote[i]>0])
    for lon,lat,expected in [(-122.452,37.795,True),(-122.489,37.836,True),
                             (-122.482,37.820,False),(-122.464,37.8108,False)]:
        if land.covers(Point(*local_xy(lon,lat)))!=expected:
            raise ValueError(f'Coast classification failed control point {(lon,lat)}')
    return land


def derive():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    old=load_data()
    terrain_grid,elev=terrain(old)

    def heights(p):
        p=np.asarray(p)
        z=np.maximum(1.65,elev(p[...,::-1]))
        return z.item() if p.ndim==1 else z

    osm=json.loads((CACHE/'osm.json').read_text(encoding='utf-8'))
    coasts,piers,ponds,greens,ballfields,beaches=[],[],[],[],[],[]
    roads,trees,supplements=[],[],[]
    counts=Counter()
    for item in osm['elements']:
        tags=item.get('tags',{})
        if item['type']=='node' and tags.get('natural')=='tree':
            x,n=map(float,local_xy(item['lon'],item['lat']))
            if ROI.covers(Point(x,n)):
                h=number(tags.get('height'),8.)
                trees.append([round(x,2),round(n,2),float(np.clip(h,3,32)),round(float(heights([x,n])),2)])
        if item['type']!='way' or len(item.get('geometry',[]))<2:
            continue
        geo=item['geometry']
        xy=np.column_stack(local_xy([p['lon'] for p in geo],[p['lat'] for p in geo]))
        line=LineString(xy)
        if not ROI.intersects(line):
            continue
        name=tags.get('name','')
        if tags.get('natural')=='coastline':
            coasts.extend(lines(line.intersection(ROI)))
        geom=Polygon(xy) if len(xy)>=4 and np.array_equal(xy[0],xy[-1]) else None
        if geom is not None and not geom.is_valid:
            geom=make_valid(geom)
            counts['repairedOSM']+=1
        if tags.get('man_made') in ('pier','breakwater','groyne'):
            pier=geom if geom is not None else line.buffer(number(tags.get('width'),7.)/2,cap_style='flat')
            piers.extend(polygons(pier.intersection(ROI)))
        if geom is not None:
            if tags.get('natural')=='water':
                ponds.extend(polygons(geom.intersection(ROI)))
            if tags.get('natural')=='beach':
                beaches.extend(polygons(geom.intersection(ROI)))
            if (tags.get('landuse') in ('grass','forest','meadow','recreation_ground','village_green')
                or tags.get('natural') in ('wood','scrub','grassland')
                or tags.get('leisure') in ('park','garden','pitch','common','nature_reserve')):
                greens.extend(polygons(geom.intersection(ROI)))
                if tags.get('sport')=='baseball':
                    ballfields.extend(polygons(geom.intersection(ROI)))
            if tags.get('building') and covered(geom):
                supplements.append((item['id'],geom.intersection(ROI),tags))
        kind=tags.get('highway')
        if not kind or kind in ('construction','proposed','abandoned','razed') or name.startswith('Golden Gate Bridge'):
            continue
        is_bridge=tags.get('bridge') not in (None,'no')
        for seg in lines(line.intersection(ROI)):
            if seg.length<2 or not covered(seg,55):
                continue
            coords=np.array(seg.coords)
            zs=heights(coords)+(.18 if not is_bridge else 2.7)
            roads.append({'id':str(item['id']),'name':name,'kind':kind,
                          'oneway':tags.get('oneway','yes' if tags.get('junction')=='roundabout' else 'no'),
                          'bridge':is_bridge,'tunnel':tags.get('tunnel') not in (None,'no'),
                          'width':float(np.clip(number(tags.get('width'),HEIGHT_CLASSES.get(kind,6)),1.4,30.)),
                          'points':np.round(np.c_[coords,zs],2).tolist()})

    # Keep park terrain on both landfalls, without interpolating over the strait.
    coast=polygon_land(coasts)
    west_land=unary_union([coast,*piers]).difference(unary_union(ponds))
    west_green=unary_union(greens).intersection(west_land)
    old_extent=box(*old['extent'])
    bounds_pts=[TO_GEO.transform(e+ORIGIN_UTM[0],n+ORIGIN_UTM[1])
                for e,n in (ground_point(x,y) for x in (ATLAS.x,ATLAS.right) for y in (ATLAS.y,ATLAS.bottom))]
    lons,lats=zip(*bounds_pts)
    context=earth_geometry('land',(min(lons)-.02,min(lats)-.02,max(lons)+.02,max(lats)+.02))
    east_land=unary_union([good_polygon(r) for r in old['land']])
    land=unary_union([west_land,east_land,context.difference(ROI.union(old_extent))])

    footprints=json.loads((CACHE/'western-footprints.geojson').read_text(encoding='utf-8'))['features']
    existing_ids={b['id'] for b in old['buildings']}
    buildings,areas=[],[]
    def add_building(identity,geom,props,source):
        if identity in existing_ids or geom.is_empty or geom.area<14 or not covered(geom,110):
            return
        pos=geom.representative_point()
        g=float(heights([pos.x,pos.y]))
        h=np.clip(number(props.get('hgt_median_m',props.get('height')),
                         number(props.get('building:levels'),2.3)*3.3),2.7,72)
        buildings.append({'id':identity,'name':props.get('name',''),'footprint':rings(geom,4),
                          'ground':round(g,2),'height':round(float(h),2),
                          'source':source,'parts':[]})
        existing_ids.add(identity)
        areas.append(geom)

    for f in footprints:
        shape_m=transform(local_xy,shape(f['geometry']))
        if not shape_m.is_valid:
            shape_m=make_valid(shape_m)
            counts['repairedDataSF']+=1
        props=f['properties']
        add_building(str(props.get('sf16_bldgid',f.get('id'))),shape_m.intersection(ROI),props,'DataSF median-height footprints')

    base_footprints=[good_polygon(poly) for b in old['buildings'] for poly in b['footprint']]
    index_shapes=areas+base_footprints
    index=STRtree(index_shapes)
    for key,geom,tags in supplements:
        if geom.is_empty or geom.area<28:
            continue
        overlaps=[index_shapes[i] for i in index.query(geom,predicate='intersects')]
        if overlaps and geom.intersection(unary_union(overlaps)).area>.3*geom.area:
            continue
        add_building(f'osm-{key}',geom,tags,'OSM footprints / height fallback')

    road_ids={r['id'] for r in old['roads']}
    roads=[r for r in roads if r['id'] not in road_ids or not all(old_extent.covers(Point(*p[:2])) for p in r['points'])]
    tree_xy={tuple(t[:2]) for t in old['trees']}
    trees=[t for t in trees if tuple(t[:2]) not in tree_xy]
    snapshot={**old,'terrain':terrain_grid,'extent':list(ROI.union(old_extent).bounds),
              'land':rings(land),'piers':old['piers']+rings(unary_union(piers)),
              'greens':old['greens']+rings(west_green),'ballfields':old['ballfields']+rings(unary_union(ballfields)),
              'beaches':rings(unary_union(beaches)), 'buildings':old['buildings']+buildings,
              'roads':old['roads']+roads,'trees':old['trees']+trees,
              'landmarks':jump_points()+old['landmarks']}
    SOURCE.write_bytes(gzip.compress(json.dumps(snapshot,separators=(',',':'),allow_nan=False).encode(),mtime=0))
    audit={'crs':'EPSG:32610','originUTM':list(ORIGIN_UTM),'extentLocalMetres':snapshot['extent'],
           'inputManifest':json.loads((CACHE/'inputs.json').read_text(encoding='utf-8')),
           'osmAcquisition':osm.get('acquisition'),'osmBase':osm.get('osm3s',{}).get('timestamp_osm_base'),
           'easternSourceSHA256':sha(ROOT/'data/corridor/source.json.gz'),'sourceSHA256':sha(SOURCE),
           'counts':{**counts,'westFootprintCandidates':len(footprints),'newBuildings':len(buildings),
                     'newRoads':len(roads),'newTrees':len(trees),'landmarks':len(snapshot['landmarks'])},
           'notes':'3DEP interpolated onto 15 m grid; v3 eastern structures retained. Natural Earth fills unillustrated margins.'}
    (OUTPUT/'provenance.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(audit['counts'],flush=True)


def load():
    return json.loads(gzip.decompress(SOURCE.read_bytes()))


if __name__=='__main__':
    derive()
