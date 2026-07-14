using System.Data;
using Microsoft.Data.SqlClient;

// Seeds CCTNS 1.0-flavoured police schema + synthetic UP Police crime data into
// Azure SQL Edge. Idempotent: drops & recreates tables. Needs only the DB.
// Swap to a real CCTNS MSSQL instance by pointing AGENT_DATABASE_URL in .env.

var repoRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", ".."));
var envPath = Path.Combine(repoRoot, ".env");
if (File.Exists(envPath)) DotNetEnv.Env.Load(envPath);

var fullConn = Environment.GetEnvironmentVariable("AGENT_DATABASE_URL")
    ?? "Server=localhost,1433;Database=CctnsUpPolice;User Id=sa;Password=Str0ngP@ssw0rd!;TrustServerCertificate=True;Connection Timeout=30;";

const string DbName = "CctnsUpPolice";

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
IF OBJECT_ID('FactCrime','U') IS NOT NULL DROP TABLE FactCrime;
IF OBJECT_ID('DimDate','U') IS NOT NULL DROP TABLE DimDate;
IF OBJECT_ID('DimDistrict','U') IS NOT NULL DROP TABLE DimDistrict;
IF OBJECT_ID('DimPoliceStation','U') IS NOT NULL DROP TABLE DimPoliceStation;
IF OBJECT_ID('DimAct','U') IS NOT NULL DROP TABLE DimAct;
IF OBJECT_ID('DimCrimeHead','U') IS NOT NULL DROP TABLE DimCrimeHead;");

Exec(db, @"
CREATE TABLE DimDate (DateKey INT PRIMARY KEY, [Date] DATE, [Year] INT, [Month] INT, MonthName NVARCHAR(20), Quarter INT, DayOfWeek NVARCHAR(12));
CREATE TABLE DimDistrict (DistrictKey INT PRIMARY KEY, DistrictName NVARCHAR(60), Zone NVARCHAR(30));
CREATE TABLE DimPoliceStation (PSKey INT PRIMARY KEY, PSName NVARCHAR(80), DistrictKey INT);
CREATE TABLE DimAct (ActKey INT PRIMARY KEY, ActName NVARCHAR(80), Section NVARCHAR(40));
CREATE TABLE DimCrimeHead (HeadKey INT PRIMARY KEY, CrimeHead NVARCHAR(60), Category NVARCHAR(40));
CREATE TABLE FactCrime (
    CrimeKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    FIRNumber NVARCHAR(30), DateKey INT, DistrictKey INT, PSKey INT,
    HeadKey INT, ActKey INT,
    IsDetected BIT,            -- crime detected (charge sheet filed) vs undetected
    IsDisposed BIT,            -- case disposed/closed vs pending
    Victims INT, Accused INT,
    [Status] NVARCHAR(20)      -- Registered / Under Investigation / ChargeSheeted / Disposed / Court
);");

var rand = new Random(42);

// --- DimDate: 2 years (2024-2025) ---
Console.WriteLine("Seeding DimDate...");
var dateKeys = new List<int>();
{
    var dt = new DataTable();
    dt.Columns.Add("DateKey", typeof(int)); dt.Columns.Add("Date", typeof(DateTime));
    dt.Columns.Add("Year", typeof(int)); dt.Columns.Add("Month", typeof(int));
    dt.Columns.Add("MonthName", typeof(string)); dt.Columns.Add("Quarter", typeof(int));
    dt.Columns.Add("DayOfWeek", typeof(string));
    var months = new[] { "January","February","March","April","May","June","July","August","September","October","November","December" };
    var days = new[] { "Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday" };
    var start = new DateTime(2024, 1, 1);
    for (int i = 0; i < 730; i++)
    {
        var d = start.AddDays(i);
        int key = d.Year * 10000 + d.Month * 100 + d.Day;
        dateKeys.Add(key);
        dt.Rows.Add(key, d, d.Year, d.Month, months[d.Month - 1], (d.Month - 1) / 3 + 1, days[(int)d.DayOfWeek]);
    }
    BulkInsert(fullConn, "DimDate", dt);
}

// --- DimDistrict (UP districts) ---
Console.WriteLine("Seeding DimDistrict...");
var districts = new[]
{
    ("Lucknow", "Central"), ("Kanpur Nagar", "Central"), ("Varanasi", "East"),
    ("Prayagraj", "Central"), ("Agra", "West"), ("Meerut", "West"),
    ("Ghaziabad", "West"), ("Noida", "West"), ("Bareilly", "West"),
    ("Aligarh", "West"), ("Gorakhpur", "East"), ("Ayodhya", "Central"),
    ("Mathura", "West"), ("Saharanpur", "West"), ("Moradabad", "West")
};
var districtKeys = Enumerable.Range(1, districts.Length).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("DistrictKey", typeof(int)); dt.Columns.Add("DistrictName", typeof(string)); dt.Columns.Add("Zone", typeof(string));
    for (int i = 0; i < districts.Length; i++)
        dt.Rows.Add(i + 1, districts[i].Item1, districts[i].Item2);
    BulkInsert(fullConn, "DimDistrict", dt);
}

// --- DimPoliceStation (2-3 PS per district) ---
Console.WriteLine("Seeding DimPoliceStation...");
var psDistrict = new Dictionary<int, int>(); int psSeq = 0;
{
    var dt = new DataTable();
    dt.Columns.Add("PSKey", typeof(int)); dt.Columns.Add("PSName", typeof(string)); dt.Columns.Add("DistrictKey", typeof(int));
    foreach (var dk in districtKeys)
    {
        int n = 2 + rand.Next(2); // 2-3 PS
        for (int j = 1; j <= n; j++)
        {
            psSeq++;
            psDistrict[psSeq] = dk;
            dt.Rows.Add(psSeq, $"{districts[dk - 1].Item1} PS-{j:D2}", dk);
        }
    }
    BulkInsert(fullConn, "DimPoliceStation", dt);
}

// --- DimAct (IPC / special acts) ---
Console.WriteLine("Seeding DimAct...");
var acts = new[]
{
    ("IPC", "302"), ("IPC", "376"), ("IPC", "379"), ("IPC", "420"),
    ("IPC", "363"), ("IPC", "354"), ("IPC", "307"), ("IPC", "394"),
    ("CrPC", "107"), ("IT Act", "66C"), ("NDPS Act", "21"), ("Excise Act", "60")
};
var actKeys = Enumerable.Range(1, acts.Length).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("ActKey", typeof(int)); dt.Columns.Add("ActName", typeof(string)); dt.Columns.Add("Section", typeof(string));
    for (int i = 0; i < acts.Length; i++) dt.Rows.Add(i + 1, acts[i].Item1, acts[i].Item2);
    BulkInsert(fullConn, "DimAct", dt);
}

// --- DimCrimeHead ---
Console.WriteLine("Seeding DimCrimeHead...");
var heads = new[]
{
    ("Murder", "Violent"), ("Rape", "Violent"), ("Kidnapping", "Violent"),
    ("Robbery", "Violent"), ("Assault", "Violent"), ("Theft", "Property"),
    ("Burglary", "Property"), ("Cheating", "Economic"), ("Cyber Crime", "Cyber"),
    ("NDPS", "Narcotics"), ("Rioting", "Public Order"), ("Drunk Driving", "Traffic")
};
var headKeys = Enumerable.Range(1, heads.Length).ToList();
{
    var dt = new DataTable();
    dt.Columns.Add("HeadKey", typeof(int)); dt.Columns.Add("CrimeHead", typeof(string)); dt.Columns.Add("Category", typeof(string));
    for (int i = 0; i < heads.Length; i++) dt.Rows.Add(i + 1, heads[i].Item1, heads[i].Item2);
    BulkInsert(fullConn, "DimCrimeHead", dt);
}

// --- FactCrime: synthetic FIRs ---
Console.WriteLine("Seeding FactCrime...");
const int FactRows = 120_000;
var statuses = new[] { "Registered", "Under Investigation", "ChargeSheeted", "Disposed", "Court" };
int firCounter = 0;
{
    var dt = new DataTable();
    dt.Columns.Add("FIRNumber", typeof(string)); dt.Columns.Add("DateKey", typeof(int));
    dt.Columns.Add("DistrictKey", typeof(int)); dt.Columns.Add("PSKey", typeof(int));
    dt.Columns.Add("HeadKey", typeof(int)); dt.Columns.Add("ActKey", typeof(int));
    dt.Columns.Add("IsDetected", typeof(bool)); dt.Columns.Add("IsDisposed", typeof(bool));
    dt.Columns.Add("Victims", typeof(int)); dt.Columns.Add("Accused", typeof(int));
    dt.Columns.Add("Status", typeof(string));

    for (int i = 0; i < FactRows; i++)
    {
        int dk = districtKeys[rand.Next(districtKeys.Count)];
        // PS must belong to that district
        int psKey;
        do { psKey = psDistrict.Keys.ElementAt(rand.Next(psDistrict.Count)); } while (psDistrict[psKey] != dk);
        int hk = headKeys[rand.Next(headKeys.Count)];
        int ak = actKeys[rand.Next(actKeys.Count)];
        firCounter++;
        string fir = $"{dk}/{(2024 + rand.Next(2))}/{firCounter:D6}";
        // detection: violent crimes detected less often; property more
        bool detected = rand.NextDouble() < (hk <= 5 ? 0.45 : 0.65);
        bool disposed = detected && rand.NextDouble() < 0.7;
        string status = disposed ? "Disposed" : (detected ? "ChargeSheeted" : statuses[rand.Next(3)]);
        dt.Rows.Add(fir, dateKeys[rand.Next(dateKeys.Count)], dk, psKey, hk, ak,
            detected, disposed, 1 + rand.Next(3), 1 + rand.Next(4), status);
        if (dt.Rows.Count == 20000)
        {
            BulkInsert(fullConn, "FactCrime", dt);
            Console.WriteLine($"  inserted {i + 1}...");
            dt.Clear();
        }
    }
    if (dt.Rows.Count > 0) BulkInsert(fullConn, "FactCrime", dt);
}

Console.WriteLine("Row counts:");
foreach (var t in new[] { "DimDate","DimDistrict","DimPoliceStation","DimAct","DimCrimeHead","FactCrime" })
{
    using var cmd = new SqlCommand($"SELECT COUNT_BIG(*) FROM {t}", db);
    Console.WriteLine($"  {t}: {cmd.ExecuteScalar()}");
}
Console.WriteLine("Seed complete.");

Console.WriteLine("Row counts:");
foreach (var t in new[] { "DimDate","DimDistrict","DimPoliceStation","DimAct","DimCrimeHead","FactCrime" })
{
    using var cmd = new SqlCommand($"SELECT COUNT_BIG(*) FROM {t}", db);
    Console.WriteLine($"  {t}: {cmd.ExecuteScalar()}");
}

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
