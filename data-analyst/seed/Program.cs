using System.Data;
using Microsoft.Data.SqlClient;

// Seeds WarehouseDemo star schema + ~100k FactSales rows into Azure SQL Edge.
// Idempotent: drops & recreates tables. Needs only the DB (no LLM key).

var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var envPath = Path.Combine(repoRoot, ".env");
if (File.Exists(envPath)) DotNetEnv.Env.Load(envPath);

var fullConn = Environment.GetEnvironmentVariable("AGENT_DATABASE_URL")
    ?? "Server=localhost,1433;Database=WarehouseDemo;User Id=sa;Password=Str0ngP@ssw0rd!;TrustServerCertificate=True;Connection Timeout=30;";

const int FactRows = 100_000;
const string DbName = "WarehouseDemo";

// Connect to master to (re)create the DB.
var masterConn = System.Text.RegularExpressions.Regex.Replace(
    fullConn, @"Database=[^;]+;", "Database=master;", System.Text.RegularExpressions.RegexOptions.IgnoreCase);

Console.WriteLine("Ensuring database exists...");
using (var conn = new SqlConnection(masterConn))
{
    conn.Open();
    Exec(conn, $"IF DB_ID('{DbName}') IS NULL CREATE DATABASE [{DbName}];");
}

using var db = new SqlConnection(fullConn);
db.Open();
Console.WriteLine("Dropping & recreating tables...");

Exec(db, @"
IF OBJECT_ID('FactSales','U') IS NOT NULL DROP TABLE FactSales;
IF OBJECT_ID('DimDate','U') IS NOT NULL DROP TABLE DimDate;
IF OBJECT_ID('DimStore','U') IS NOT NULL DROP TABLE DimStore;
IF OBJECT_ID('DimProduct','U') IS NOT NULL DROP TABLE DimProduct;
IF OBJECT_ID('DimChannel','U') IS NOT NULL DROP TABLE DimChannel;");

Exec(db, @"
CREATE TABLE DimDate (DateKey INT PRIMARY KEY, [Date] DATE, [Year] INT, [Month] INT, MonthName NVARCHAR(20), Quarter INT, DayOfWeek NVARCHAR(12));
CREATE TABLE DimStore (StoreKey INT PRIMARY KEY, StoreName NVARCHAR(60), Region NVARCHAR(30), City NVARCHAR(40));
CREATE TABLE DimProduct (ProductKey INT PRIMARY KEY, ProductName NVARCHAR(60), Category NVARCHAR(40), Brand NVARCHAR(40));
CREATE TABLE DimChannel (ChannelKey INT PRIMARY KEY, ChannelName NVARCHAR(30));
CREATE TABLE FactSales (SalesKey BIGINT IDENTITY(1,1) PRIMARY KEY, DateKey INT, StoreKey INT, ProductKey INT, ChannelKey INT, Quantity INT, Amount DECIMAL(12,2));");

var rand = new Random(42);

// --- DimDate: 2 years ---
Console.WriteLine("Seeding DimDate...");
var dateKeys = new List<int>();
var months = new[] { "January","February","March","April","May","June","July","August","September","October","November","December" };
var days = new[] { "Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday" };
{
    var start = new DateTime(2024, 1, 1);
    var dt = new DataTable();
    dt.Columns.Add("DateKey", typeof(int)); dt.Columns.Add("Date", typeof(DateTime));
    dt.Columns.Add("Year", typeof(int)); dt.Columns.Add("Month", typeof(int));
    dt.Columns.Add("MonthName", typeof(string)); dt.Columns.Add("Quarter", typeof(int));
    dt.Columns.Add("DayOfWeek", typeof(string));
    for (int i = 0; i < 730; i++)
    {
        var d = start.AddDays(i);
        int key = d.Year * 10000 + d.Month * 100 + d.Day;
        dateKeys.Add(key);
        dt.Rows.Add(key, d, d.Year, d.Month, months[d.Month - 1], (d.Month - 1) / 3 + 1, days[(int)d.DayOfWeek]);
    }
    BulkInsert(fullConn, "DimDate", dt);
}

// --- DimStore ---
Console.WriteLine("Seeding DimStore...");
var regions = new[] { "North","South","East","West","Central" };
var cities = new[] { "Seattle","Austin","Boston","Denver","Miami","Chicago","Phoenix","Atlanta" };
var storeKeys = Enumerable.Range(1, 20).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("StoreKey", typeof(int)); dt.Columns.Add("StoreName", typeof(string));
    dt.Columns.Add("Region", typeof(string)); dt.Columns.Add("City", typeof(string));
    foreach (var k in storeKeys)
        dt.Rows.Add(k, $"Store {k:D2}", regions[rand.Next(regions.Length)], cities[rand.Next(cities.Length)]);
    BulkInsert(fullConn, "DimStore", dt);
}

// --- DimProduct ---
Console.WriteLine("Seeding DimProduct...");
var categories = new[] { "Electronics","Grocery","Apparel","Home","Toys","Sports" };
var brands = new[] { "Acme","Globex","Umbrella","Initech","Hooli","Stark" };
var productKeys = Enumerable.Range(1, 200).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("ProductKey", typeof(int)); dt.Columns.Add("ProductName", typeof(string));
    dt.Columns.Add("Category", typeof(string)); dt.Columns.Add("Brand", typeof(string));
    foreach (var k in productKeys)
        dt.Rows.Add(k, $"Product {k:D3}", categories[rand.Next(categories.Length)], brands[rand.Next(brands.Length)]);
    BulkInsert(fullConn, "DimProduct", dt);
}

// --- DimChannel ---
Console.WriteLine("Seeding DimChannel...");
var channels = new[] { "Online","Retail","Wholesale","Partner" };
var channelKeys = Enumerable.Range(1, channels.Length).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("ChannelKey", typeof(int)); dt.Columns.Add("ChannelName", typeof(string));
    for (int i = 0; i < channels.Length; i++) dt.Rows.Add(i + 1, channels[i]);
    BulkInsert(fullConn, "DimChannel", dt);
}

// --- FactSales: ~100k rows ---
Console.WriteLine($"Seeding FactSales ({FactRows} rows)...");
{
    var dt = new DataTable();
    dt.Columns.Add("DateKey", typeof(int)); dt.Columns.Add("StoreKey", typeof(int));
    dt.Columns.Add("ProductKey", typeof(int)); dt.Columns.Add("ChannelKey", typeof(int));
    dt.Columns.Add("Quantity", typeof(int)); dt.Columns.Add("Amount", typeof(decimal));
    for (int i = 0; i < FactRows; i++)
    {
        int qty = rand.Next(1, 20);
        decimal unit = (decimal)(rand.NextDouble() * 95 + 5);
        dt.Rows.Add(
            dateKeys[rand.Next(dateKeys.Count)],
            storeKeys[rand.Next(storeKeys.Count)],
            productKeys[rand.Next(productKeys.Count)],
            channelKeys[rand.Next(channelKeys.Count)],
            qty, Math.Round(qty * unit, 2));
        if (dt.Rows.Count == 20000)
        {
            BulkInsert(fullConn, "FactSales", dt);
            Console.WriteLine($"  inserted {i + 1}...");
            dt.Clear();
        }
    }
    if (dt.Rows.Count > 0) BulkInsert(fullConn, "FactSales", dt);
}

// --- Verify ---
Console.WriteLine("Row counts:");
foreach (var t in new[] { "DimDate","DimStore","DimProduct","DimChannel","FactSales" })
{
    using var cmd = new SqlCommand($"SELECT COUNT_BIG(*) FROM {t}", db);
    Console.WriteLine($"  {t}: {cmd.ExecuteScalar()}");
}
Console.WriteLine("Seed complete.");

static void Exec(SqlConnection conn, string sql)
{
    using var cmd = new SqlCommand(sql, conn) { CommandTimeout = 120 };
    cmd.ExecuteNonQuery();
}

static void BulkInsert(string connStr, string table, DataTable dt)
{
    using var conn = new SqlConnection(connStr);
    conn.Open();
    using var bulk = new SqlBulkCopy(conn) { DestinationTableName = table, BulkCopyTimeout = 300 };
    foreach (DataColumn c in dt.Columns)
        bulk.ColumnMappings.Add(c.ColumnName, c.ColumnName);
    bulk.WriteToServer(dt);
}
