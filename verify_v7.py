import json
d = json.load(open('live_data.json'))
r = d[0]
keys = ['TyreInnerFL','TyreSurfFL','BrakeTempFL','DRS','Weather','TrackTemp','GapAhead','CarPosition','Hız','RPM','ERS','LapNum']
for k in keys:
    print(f"{k}: {r.get(k, 'MISSING')}")
