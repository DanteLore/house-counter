# ONS Inflation Data

Monthly UK inflation time series from the ONS MM23 dataset, covering CPI, CPIH
and RPI from as far back as June 1948. Loaded as a single wide Parquet file with
one row per year/month.

## Schema

**Glue table:** `incoming.ons_inflation_inflation`
**S3 location:** `s3://dantelore.data.incoming/ons_inflation/inflation/inflation.parquet`

| Field | Type | Description |
|---|---|---|
| `year` | int | Year |
| `month` | int | Month number (1–12) |
| `cpi_index` | double | CPI index (2015=100) — absolute price level, from Jan 1988 |
| `cpi_rate` | double | CPI 12-month rate % — year-on-year change, from Jan 1989 |
| `cpih_index` | double | CPIH index (2015=100) — CPI including owner-occupier costs, from Jan 1989 |
| `cpih_rate` | double | CPIH 12-month rate % — year-on-year change, from Jan 1988 |
| `rpi_rate` | double | RPI 12-month rate % — year-on-year change, from Jun 1948 |

No partition key — the table is small (934 rows) and always scanned in full.

## Which measure to use

- **CPI** — the UK's headline inflation measure since 2003, used by the Bank of England
  for its 2% target. Best for deflating recent data (1988+).
- **CPIH** — CPI plus owner-occupiers' housing costs. ONS's preferred measure since 2017.
  Slightly smoother than CPI.
- **RPI** — older measure, no longer a National Statistic but still widely used in
  contracts and index-linking. The only series with data before 1988.

For deflating house prices use `cpi_index` — divide the nominal price by the index
value for that month, then multiply by 100 to express in 2015 pounds.

## Common queries

### View the full series

```sql
SELECT year, month, cpi_index, cpi_rate, rpi_rate
FROM ons_inflation_inflation
ORDER BY year, month
```

### Latest inflation figures

```sql
SELECT *
FROM ons_inflation_inflation
ORDER BY year DESC, month DESC
LIMIT 6
```

### Annual average CPI rate by year

```sql
SELECT year, ROUND(AVG(cpi_rate), 2) AS avg_cpi_rate
FROM ons_inflation_inflation
WHERE cpi_rate IS NOT NULL
GROUP BY year
ORDER BY year DESC
```

### Deflating house prices to real terms (2015 £)

Join on year and month to bring in the CPI index, then divide the nominal price
by the index and multiply by 100.

```sql
SELECT
    p.year,
    p.town_city,
    p.postcode,
    p.price                                                        AS nominal_price,
    i.cpi_index,
    ROUND(CAST(p.price AS double) / i.cpi_index * 100)            AS real_price_2015
FROM house_prices_ppd p
JOIN ons_inflation_inflation i
    ON  CAST(p.year AS int) = i.year
    AND CAST(SUBSTR(p.date_of_transfer, 6, 2) AS int) = i.month
WHERE p.year = '2010'
  AND p.town_city = 'NEWBURY'
ORDER BY real_price_2015 DESC
LIMIT 20
```

Note: `house_prices_ppd` is partitioned by `year` (string). `date_of_transfer` contains
a time component (`2010-12-02 00:00`) so use `SUBSTR(..., 6, 2)` to extract the month
rather than `DATE()` or `MONTH()`.

### Cumulative inflation between two dates

How much has £100 in January 2000 grown to in today's money?

```sql
WITH base AS (
    SELECT cpi_index FROM ons_inflation_inflation WHERE year = 2000 AND month = 1
),
latest AS (
    SELECT cpi_index FROM ons_inflation_inflation ORDER BY year DESC, month DESC LIMIT 1
)
SELECT ROUND(latest.cpi_index / base.cpi_index * 100, 2) AS equivalent_value
FROM base, latest
```

### Years with highest inflation (CPI)

```sql
SELECT year, ROUND(AVG(cpi_rate), 1) AS avg_cpi_rate
FROM ons_inflation_inflation
WHERE cpi_rate IS NOT NULL
GROUP BY year
ORDER BY avg_cpi_rate DESC
LIMIT 10
```

## Source and update cadence

**Source:** ONS MM23 dataset, fetched via:
```
https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/{series}/mm23/data
```

Series IDs: `l522` (CPI index), `d7g7` (CPI rate), `l55o` (CPIH index),
`d7bt` (CPIH rate), `czbh` (RPI rate).

No authentication required. ONS publish updated figures monthly, typically on the
third Wednesday. Re-run the loader to pick up the latest month:

```bash
python ons_inflation/ons_inflation_load.py
```
