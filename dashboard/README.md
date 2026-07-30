# Dashboard guide

Run `pnpm run dev` from the project root and open the printed local URL.

## Controls

- **Year, state, specialty, class, marketed-name type, provider decile:** filter the aggregated dashboard cube.
- **Search:** filters the visible opportunity table by state.
- **Download CSV:** exports the currently searched opportunity rows.
- **Methodology & limitations:** opens the scope, definitions, score weights, and CMS caveats.
- **Reset filters:** restores the national latest-year view.

The product ranking, Lorenz curve, and product scatter are labeled national because the compact public dashboard payload stores those analyses at national grain. Other KPI, class, geography, and specialty views use the filter cube. Empty filter combinations display a clear no-data state.

The footer always shows the official CMS source, 2024 latest reporting year, source modified date, and the central interpretation limits.

