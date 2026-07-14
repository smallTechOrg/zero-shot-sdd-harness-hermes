# Data — Warehouse Schema & Seed

## Star Schema (WarehouseDemo)

### FactSales
| Column      | Type          | Notes                       |
|-------------|---------------|-----------------------------|
| SalesKey    | BIGINT IDENTITY PK |                        |
| DateKey     | INT FK → DimDate.DateKey |               |
| StoreKey    | INT FK → DimStore.StoreKey |             |
| ProductKey  | INT FK → DimProduct.ProductKey |         |
| ChannelKey  | INT FK → DimChannel.ChannelKey |         |
| Quantity    | INT           |                             |
| Amount      | DECIMAL(12,2) |                             |

### DimDate
DateKey (INT PK, yyyymmdd), Date (DATE), Year, Month, MonthName, Quarter, DayOfWeek.

### DimStore
StoreKey (INT PK), StoreName, Region, City.

### DimProduct
ProductKey (INT PK), ProductName, Category, Brand.

### DimChannel
ChannelKey (INT PK), ChannelName (Online, Retail, Wholesale, Partner).

## Seed Plan

- ~730 days of DimDate (2 years), 20 stores, 200 products, 4 channels.
- ~100,000 FactSales rows generated with plausible random distributions.
- Bulk-inserted in batches for speed.
- Idempotent: drops & recreates WarehouseDemo tables on run.

## Aggregate Profiles (sent to LLM)

For each table: row count. For each column: distinct count, null%, and for
numeric columns min/max/avg. Computed via sampled aggregate queries and cached
in memory. RAW ROWS ARE NEVER PROFILED OUT TO THE LLM.
