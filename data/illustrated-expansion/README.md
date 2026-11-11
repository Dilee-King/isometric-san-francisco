# Registration and transport

The compressed routing files and packed mask are retained from the previous versioned scenes. They supply the fixed map projection, source visibility and the car, vessel and aircraft paths. The reference geometry and source hashes are recorded in [the inner Bay source provenance](../inner-bay/provenance.json).

The East Bay corrections record OpenStreetMap coastline polygons for Ballena Isle and Coast Guard Island and the Lake Merritt water polygon. Each feature includes the upstream ID and source digest. They adjust the water flag in the packed visibility mask. [OpenStreetMap attribution and license](https://www.openstreetmap.org/copyright)
