# Illustrated expansion

The built-in ImageGen tool extends the v0.5 artwork across San Francisco and the inner Bay. Each selected PNG in `plates` has its exact prompt alongside it. The `-night` suffix marks a rainy-night edit of its daylight plate. The `-dry-night` and `-rain-day` edits for Civic Center, Jack London Square and Sausalito use the corresponding v0.5 Wharf artwork as a lighting and material reference.

The layout records each frame on the original fixed 39° camera. Area plates carry the illustration across adjacent neighborhoods and shorelines. Detail plates bring the named locations to the original pixel scale. Later waves use artwork from the preceding overlaps to continue roads, coastlines and bridge decks.

Use `python tools/illustrated_guides.py --ids <plate-id>` to generate a drawing guide from the retained geographic references and available neighboring artwork. The guide supplies placement. The tile builder combines the selected ImageGen imagery with the v0.5 imagery and offshore field.
