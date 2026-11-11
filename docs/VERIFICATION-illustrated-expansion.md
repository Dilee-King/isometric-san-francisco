# Illustrated San Francisco and the inner Bay

The three cumulative releases extend the approved v0.5 artwork with the built-in ImageGen tool. Each pass uses completed neighboring art and registered geographic guide coordinates. The new neighborhood, bridge, park and waterfront images come from the selected illustrations. The source snapshot supplies the projection, coastline and street guide, visibility mask, lighting positions and transport paths. [Selected plates and exact prompts](../assets/illustrated-expansion/)

| Release | Coverage added | New area plates | New native detail plates |
| --- | --- | ---: | ---: |
| v0.6.1 | San Francisco mainland and islands, both Bay Bridge spans and Oakland landfall | 91 | 24 |
| v0.7.1 | Port of Oakland, Jack London Square and both Alameda ferry terminals | 23 | 5 |
| v0.8.1 | Golden Gate north landing, Fort Baker, Bridgeway and Sausalito | 9 | 4 |

All selected daylight images are 1536 × 1024. The area plates span 3072 × 2048 on the atlas and overlap to maintain continuity. Native details use the original 1.854545 pixels per metre. The registered plate bounds cover all three planned geographic footprints when combined with the accepted v0.5 art. A separate wide ImageGen plate extends the southern peninsula at distant zoom. The Bay Area view provides the wider geographic context.

The packer blends narrow overlaps, matches offshore water to the v0.5 field and retains image-generated bridge structures over that field. Two measured image-space corrections follow the illustrated bridge carriageways while the existing renderer still projects and depth-tests the original vehicle geometry. The East Bay mask restores Lake Merritt and two shoreline islands from the recorded OpenStreetMap polygons. Building outlines, lanes and coastal details are illustrative. [Registration data](../data/illustrated-expansion/)

The four appearance pyramids share one projection. Each release enables the relevant regions and uses stage-specific tiles where an illustration crosses a release boundary. The original controls provide independent traffic toggles, daylight and night, clear weather, coastal fog and wet materials.

The five paired wet-night edits cover Civic Center, Bayview, the Bay Bridge East Span, Jack London Square and Sausalito. Local Chromium compared Jack London Square's dry and wet day layers with the moving precipitation hidden. The mean absolute difference over a 780 × 600 crop was 14.05 on the 0–255 RGB scale.

## Local browser verification

The production build passed 28 JavaScript tests, 14 Python tests, the historical atlas audits and the illustrated expansion audit. Chromium opened each release from a fresh page. Each started with 20 regional detail requests, all for the initial map and active appearance. Real pointer drags crossed from Union Square into Civic Center and from the Bay Bridge into Oakland. The browser verified cars on both spans, ferry traffic at Jack London Square and Sausalito, aircraft toggles, wet day and wet night layers, coastal fog, and retention of time and weather when switching between the city and Bay Area. The mobile view loaded the rain layer at 390 × 844 without horizontal overflow. Chromium reported zero page or console errors and zero failed HTTP responses during this check.

[Browser drag recording](Illustrated-Inner-Bay-actual-demo.mp4) · [Citywide San Francisco](screenshots/v0.6.1/san-francisco-wide.jpg) · [Jack London Square in rain](screenshots/v0.7.1/jack-london-rain-night.jpg) · [Sausalito in rain](screenshots/v0.8.1/sausalito-rain-night.jpg)

## GitHub Pages verification

The [build and deployment](https://github.com/Dilee-King/isometric-san-francisco/actions/runs/42969571226) completed successfully for a0a6445fbf153aa7a14b9ca824f3639dce4e0bad. Chromium passed the same city, bridge, East Bay and Marin interactions on all three published URLs. Each opened with 20 visible detail requests and reported zero page, console or HTTP errors. The public default opened v0.8.1, the old v0.8.0 URL resolved to the illustrated edition, and the v0.5.0 URL opened the original city scene. SHA-256 matched 49 served files against the local build inputs, including the atlases, manifests, shared mask and sampled tiles in all four appearances.

[San Francisco on Pages](screenshots/v0.6.1/online-san-francisco-wide.jpg) · [Bay Bridge East Span on Pages](screenshots/v0.6.1/online-bay-bridge-east.jpg) · [Jack London Square on Pages](screenshots/v0.7.1/online-jack-london-rain-night.jpg) · [Sausalito on Pages](screenshots/v0.8.1/online-sausalito-rain-night.jpg)

## Night and rain alignment

The expanded atlas now uses the original v0.5 depth mask to determine visibility for retained window and street lights. The expanded vehicle mask continues to handle moving traffic. New districts use the v0.5 light-baking pass on window details sampled from the illustrations. Rain uses a cooler overcast exposure calibrated to the Wharf, Pier 39 and Mission Bay artwork, with specular highlights on paving and wet-night reflections near lamps.

Six ImageGen variants match the v0.5 Wharf clear-night and rainy-day plates at Civic Center, Jack London Square and Sausalito. All six are 1536 × 1024 with at most one pixel of overall edge displacement against the clear-day originals. Their source PNGs and prompts are checked in. [Selected plates and prompts](../assets/illustrated-expansion/plates/)

At distant zoom, the atlas equalizes rainy-day exposure and tapers amber light where the original and expanded artwork meet. The opacity of the retained lamp sprites follows zoom to keep closely spaced lights legible.

Chromium compared the Union Square lighting overlay at the same camera and time in all four versions. Each produced 8,293 lit pixels and the same summed alpha in the measured crop. The comparison also includes the three weather states at the Wharf and the three new locations. The daytime material changed in each location with the rain animation hidden. [Browser comparison](screenshots/weather-alignment.jpg) · [Browser verification script](../tools/qa-weather-alignment.js)

## Landmark detail repairs

The visual review covered 35 browser views across the three cumulative releases. The independent Illustrated map was used to compare landmark scale, road hierarchy and streetscape detail. [Union Square reference](https://isometricsanfrancisco.com/#m=illustration&x=67292&y=26745&s=0.908&p=union_square)

| Release | Selected edits | Location references |
| --- | --- | --- |
| v0.6.1 | Distinct Queen Anne rooflines along Steiner Street, and a more legible Twin Peaks access road, lookout and firefighting reservoir | [San Francisco Planning](https://default.sfplanning.org/Preservation/walking_tours/Walking_Tour_ALAMO_SQUARE.pdf) · [Twin Peaks topographic plan](https://sfrecpark.org/DocumentCenter/View/19817/2022-Twin-Peaks-Map) |
| v0.7.1 | Ship-to-shore gantries and container handling lanes in Oakland, and the covered passenger pier, gangway and floating berth at Seaplane Lagoon | [Port of Oakland](https://www.portofoakland.com/port-oakland-begins-project-raise-height-four-cranes) · [Alameda terminal plan](https://alameda.legistar.com/View.ashx?GUID=D6328AA8-B0ED-48BA-A04F-4F9B0FBFD692&ID=6199148&M=F) |
| v0.8.1 | Clearer separation of the Fort Baker launch ramp, fishing pier and marina, and more legible shore connections and working sheds in Sausalito | [National Park Service](https://www.nps.gov/goga/planyourvisit/fort-baker.htm) · [City of Sausalito](https://www.sausalito.gov/community/transportation/harbors_and_marinas.php) |

The six registered ImageGen edits use the original 1536 × 1024 frame. The full-frame edge-correlation peak was within one pixel for each edit. Small offshore paint masks keep the Oakland crane arms and the Seaplane boarding platform visible above the shared water texture. [Before-and-after browser captures](screenshots/detail-repairs.jpg)

The Fort Baker detail takes precedence inside a feathered part of the v0.8.1 plate. This exposes the cove repair while joining the retained bridge artwork at the perimeter. A tonal transition is still visible on the eastern bluff.

Chromium visited all six views and used pointer drags to cross their surrounding tile edges. It loaded the daytime rain, dry night and rainy night layers in each release with no page or HTTP errors. A separate regional regression checked the startup requests, bridge cars and ferry rendering. Tile manifests and scene data were checked against the previous releases for coverage, route coordinates, surface masks and the earlier paired weather illustrations.
