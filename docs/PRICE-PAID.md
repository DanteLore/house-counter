# Land Registry Price Paid Data

Every residential property sale in England & Wales registered with HM Land Registry since 1995.

**Source:** https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads  
**Glue database:** `incoming`  
**Glue table:** `incoming.house_prices_ppd`  
**S3 location:** `s3://dantelore.data.incoming/house_prices/ppd/`  
**Format:** Parquet (SNAPPY compressed)  
**Time range:** 1995 – present (updated monthly)

---

## Partitioning

The table is partitioned by **`year`** (string), derived from the transaction date.

```
s3://dantelore.data.incoming/house_prices/ppd/year=2024/ppd_2024.parquet
```

Always filter on `year` in Athena queries to avoid full-table scans:

```sql
WHERE year = '2024'
-- or for a range:
WHERE year BETWEEN '2010' AND '2024'
```

---

## Schema

| Column | Type | Description |
|---|---|---|
| `transaction_id` | string | HMLR-assigned UUID, unique per transaction. Format: `{xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}` |
| `price` | bigint | Sale price in GBP (pounds sterling) |
| `date_of_transfer` | string | Date the sale completed. Format: `YYYY-MM-DD HH:MM` (time is always `00:00`) |
| `postcode` | string | UK postcode of the property. May be null for some older records |
| `property_type` | string | See [Property Type codes](#property-type) below |
| `old_new` | string | `Y` = newly built; `N` = established residential building |
| `duration` | string | `F` = freehold; `L` = leasehold; `U` = unknown |
| `paon` | string | Primary Addressable Object Name  -  house number or name |
| `saon` | string | Secondary Addressable Object Name  -  flat/unit within a building. May be null |
| `street` | string | Street name |
| `locality` | string | Locality / village name. May be null |
| `town_city` | string | Town or city |
| `district` | string | Local government district |
| `county` | string | County |
| `ppd_category_type` | string | See [PPD Category Type codes](#ppd-category-type) below |
| `record_status` | string | See [Record Status codes](#record-status) below |
| `year` | string | **Partition key.** Derived from `date_of_transfer`. Values: `1995`–present |

---

## Code Reference

### Property Type

| Code | Meaning |
|---|---|
| `D` | Detached |
| `S` | Semi-detached |
| `T` | Terraced |
| `F` | Flats / maisonettes |
| `O` | Other (non-standard property types) |

### PPD Category Type

| Code | Meaning |
|---|---|
| `A` | Standard Price Paid entry  -  full residential market transaction |
| `B` | Additional Price Paid entry  -  transfer under a power of sale / repossession, buy-to-let, or first-time buyer arrangement |

### Record Status

| Code | Meaning |
|---|---|
| `A` | Addition  -  new record |
| `C` | Change  -  amendment to a previously published record |
| `D` | Delete  -  record removed from the dataset |

---

## Example Athena Queries

**Count sales by property type for a given year:**
```sql
SELECT property_type, COUNT(*) AS sales
FROM incoming.house_prices_ppd
WHERE year = '2023'
GROUP BY property_type
ORDER BY sales DESC;
```

**Median price by county (2020–2024):**
```sql
SELECT county,
       approx_percentile(price, 0.5) AS median_price,
       COUNT(*) AS transactions
FROM incoming.house_prices_ppd
WHERE year BETWEEN '2020' AND '2024'
  AND ppd_category_type = 'A'
GROUP BY county
ORDER BY median_price DESC;
```

**All sales in a postcode district:**
```sql
SELECT date_of_transfer, price, paon, saon, street, property_type, duration
FROM incoming.house_prices_ppd
WHERE year = '2024'
  AND postcode LIKE 'SW1A%'
ORDER BY date_of_transfer DESC;
```

**Parse the transfer date as a proper timestamp:**
```sql
SELECT transaction_id,
       date_parse(date_of_transfer, '%Y-%m-%d %H:%i') AS transfer_date,
       price
FROM incoming.house_prices_ppd
WHERE year = '2024'
LIMIT 100;
```

---

## Notes

- The dataset covers **England and Wales only**  -  Scotland and Northern Ireland are not included.
- `postcode` is occasionally null for older records (pre-2000).
- `saon` is null for houses; only populated for flats and units within subdivided buildings.
- Records with `record_status = 'D'` are deletions and should typically be excluded from analysis: `WHERE record_status != 'D'`.
- For market analysis, filter to `ppd_category_type = 'A'` (standard transactions) to exclude repossessions and atypical transfers.
- `price` is stored as `bigint`; cast to `double` before arithmetic (e.g. averages): `AVG(CAST(price AS double))`.
- Data is published monthly  -  re-run the loader for the current year to pick up new transactions.
