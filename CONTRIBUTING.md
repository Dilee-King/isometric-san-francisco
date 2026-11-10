# Contributing

The repository currently contains a design, not a running map. Check [ROADMAP](ROADMAP.md) and the [project design](docs/project-design.md) before starting a feature.

For a tile issue, include the release/tile ID, zoom level, expected real feature and an optional screenshot without private browser content. Describe seams, shifted streets, roofs, water colors or incorrect vegetation precisely. Use the tile-quality issue template.

For transport or effects, state the scenario, expected motion and observed behavior. Keep world coordinates and one shared projection. Preserve pause, toggles, depth ordering, reduced motion and mobile interaction.

Submit small, scoped changes with an accurate change description and relevant evidence. Add meaningful tests for route, clock and coordinate invariants when implementing behavior. Validate artwork in actual viewer screenshots. Do not create passing-check or coverage claims before runnable code/data exists.

Never commit secrets, raw imagery, unreviewed third-party assets, model weights, local machine paths or unrelated project outputs. Preserve upstream notices for code actually reused and provenance for every published asset.
