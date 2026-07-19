# Capabilities

## Core Capabilities

### 1. Natural Language to SQL (NL→SQL)
**Description:** Convert natural language queries about UP Police data into optimized T-SQL queries with built-in guards against expensive operations.
- **Input:** Natural language question (e.g., "Show me murder cases in Lucknow district from January 2024")
- **Process:** Schema-aware prompting → T-SQL generation → Guard application (double-TOP, non-T-SQL rejection, try/catch) → Execution against cache/replica
- **Output:** SQL query, results, execution metrics, and explanatory notes
- **Guards:** 
  - Double-TOP injection for row limiting
  - Non-T-SQL function rejection (LPAD/RPAD/DATE_FORMAT/etc.)
  - Try/catch wrapping returning structured 400 on SqlException
  - SELECT * forbidden; explicit column selection required
  - Query timeout enforcement

### 2. Semantic Layer
**Description:** Pre-built semantic models for common police analytics metrics and dimensions.
- **Pre-defined Metrics:** 
  - Detection Rate = (Chargesheeted FIRs / Total FIRs) * 100
  - Pendency Age = Current Date - FIR Registration Date
  - Monthly Trends = FIRs registered per month by district/crime type
  - Disposal Rate = (Disposed FIRs / Total FIRs) * 100
- **Dimensions:** District, Police Station, Crime Head, IPC Section, FIR Status, Date ranges
- **Usage:** Dashboard components and reports reference semantic metrics directly
- **Fallback:** If semantic layer doesn't cover query, falls back to NL→SQL

### 3. Dashboard & Visualization Engine
**Description:** Interactive dashboards with drill-down capabilities for police leadership.
- **Executive Dashboard:** State-level trends, detection rates, pendency aging, top crime types
- **District Dashboard:** District-specific metrics, station comparisons, trend analysis
- **Station Dashboard:** Station-level FIR counts, case status, investigation timelines
- **Features:** 
  - Date range selectors
  - Drill-down by geography (state→district→station) and crime hierarchy
  - Export to CSV/PDF
  - Refresh controls with caching indicators
  - Role-based visibility (DGP sees all, SP sees district, SHO sees station)

### 4. Ad-hoc Query Interface
**Description:** Natural language query interface with instant results and guidance.
- **Query Input:** Free-form natural language with autocomplete suggestions
- **Query Assistance:** 
  - Schema-aware examples ("Show FIRs by district", "Detection rate trends")
  - Query validation and optimization hints
  - Execution time estimates
- **Results Display:** 
  - Tabular data with sorting/filtering
  - Key metrics cards (totals, averages, percentages)
  - Automatic chart suggestions based on data types
  - Download options (CSV, Excel)

### 5. Scheduled Reporting
**Description:** Automated report generation and delivery for leadership consumption.
- **Report Types:** 
  - Daily FIR summary (district-wise counts)
  - Weekly crime trend analysis
  - Monthly detection/pendency reports
  - Custom ad-hoc reports
- **Delivery:** 
  - Email distribution lists (role-based)
  - Secure file share notifications
  - Dashboard notifications
- **Scheduling:** Cron-based with retry logic and failure alerts

### 6. Data Caching & ETL
**Description:** Efficient data synchronization from MsSQL to local cache for low-latency queries.
- **ETL Process:** 
  - Nightly incremental loads from MsSQL read replicas
  - Columnstore-indexed fact tables (t_fir_registration, t_final_report)
  - Dimension table synchronization (m_police_station, m_district, m_crime_head, m_ipc_section)
  - Parquet partitioning by date and district for query pruning
- **Cache Management:**
  - 20GB SSD limit enforced via retention policies
  - Hot/warm/cold data tiering (recent 90 days hot, 90-365 days warm, older archived)
  - Cache freshness indicators in UI
  - Fallback to read replicas for stale-or-missing data

### 7. Security & Access Control
**Description:** Role-based and column-level security for sensitive police data.
- **Role-Based Access:** 
  - DGP/ADG/IG: State-wide access
  - SP/IG: District/range access only
  - SHO/IO: Station-level access only
  - Analysts: Configurable access based on assignment
- **Column Masking:** 
  - PII fields (victim/accused names, phone, address) masked by role
  - Case-sensitive information restricted to investigators
  - Audit trail for all data access
- **Network Security:** 
  - No cloud egress for raw data
  - VPC-restricted OpenRouter access (if cloud LLM used)
  - Encrypted data at rest and in transit

### 8. Performance & Monitoring
**Description:** Monitoring, alerting, and performance optimization for SLAs.
- **SLAs:** 
  - Sub-second response for cached queries
  - <5s for complex aggregations
  - 99.9% uptime for critical dashboards
- **Monitoring:** 
  - Query performance tracking
  - Cache hit/miss ratios
  - LLM API usage and latency
  - Error rates and failure patterns
- **Alerting:** 
  - SLA breaches
  - Cache staleness warnings
  - LLM service degradation
  - Database connectivity issues