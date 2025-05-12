from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain.prompts import PromptTemplate
import re

business_term_mapping = {
    "UBC": "COUNT(DISTINCT CustomerID)",
    "unique billing count": "COUNT(DISTINCT CustomerID)",
    "milk DTM":"DTM",
    "net amount": "SUM(NetAmount) NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "sales quantity": "SUM(SalesQuantity)/time period NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "total tax": "SUM(TotalTax)",
    "total amount": "SUM(TotalAmount) NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "butter milk": "buttermilk",
    "butter Milk": "buttermilk",
    "Butter Milk": "buttermilk",
    "Sales office":"Sales Offcie Type",
    "sales office":"Sales Offcie Type",
    "city": "CITY",
    "state": "STATE",
    "Sales zone": "Sales_Zone",
    "sale zone": "Sales_Zone",
    "REGION NAME": "REGION_NAME",
    "region name": "REGION_NAME",
    "area name": "AREA_NAME",
    "short Name": "Short_Name",
    "short name":"Short_Name",
    "sales Office type": "Sales Offcie Type",
    "zone level sk": "Zone_Level_SK",
    "state level sk": "State_Level_SK",
    "city level sk" : "City_Level_SK",
    "sales office level sk": "SalesOffice_Level_SK",
    "Sales office level sk": "SalesOffice_Level_SK",
    "sol sk": "SalesOffice_Level_SK",  
    "sot": "Sales Offcie Type",  
    "hyderabad":"hyd",
    "solsk": "SalesOffice_Level_SK",
    "Toned Milk":"TM",
    "toned milk":"TM",
    "tg 2":"TG-2",
    "kothakoata":"B.KOTHAKOTA",
    "ap 1": "AP-1",
    "ap 2": "AP-2",
    "ap 3": "AP-3",
    "AP 1": "AP-1",
    "AP 2": "AP-2",
    "TG 1": "TG-1",
    "tg 1": "TG-1",
    "KA": "KA",
    "z4": "Z-4",
    "z 4": "Z-4",
    "Z 4": "Z-4",
    "andhra pradesh":"ANDHRA PRADESH",
    "ap": "ANDHRA PRADESH",
    "andhra":"ANDHRA PRADESH",
    "AP":"ANDHRA PRADESH",
    "Tamil nadu":"TAMIL NADU",
    "tamil nadu":"TAMIL NADU",
    "TN":"TAMIL NADU",
    "PUNJAB":"PUNJAB",
    "punjab":"PUNJAB", 
    "GUJARAT":"GUJARAT",
    "gujarat":"GUJARAT",
    "HARYANA":"HARYANA",
    "haryana":"HARYANA",
    "harayana":"HARYANA",
    "hariyana":"HARYANA",
    "RAJASTHAN":"RAJASTHAN",
    "rajasthan":"RAJASTHAN",
    "NIZAMABAD":"NIZAMABAD",
    "nizamabad":"NIZAMABAD",
    "RAI":"RAI",
    "rai":"RAI",
    "chennai sales office 5":"Chennai Sales Office - 5",
    "chennai sales office 3":"Chennai Sales Office - 3",
    "bangalore sales office 1":"Bangalore Sales Office - 1",
    "export sales office KA":"Export Sales Office - KA",
    "coimbattore sales office":"COIMBATTORE SALES OFFICE",
    "HYDERABAD-2":"HYDERABAD-2",
    "hyd 2":"HYDERABAD-2",
    "HYDERABAD-1":"HYDERABAD-1",
    "hyd 1":"HYDERABAD-1",
    "lastweek":  "last week",
    "ytd": "year to date",
    "mtd": "month to date",
    "qtd": "quarter to date",
    "wtd": "week to date",
    "last 7 days": "last 7 days",
    "total volume": "SUM(SalesQuantity)/time period NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "sales": "SUM(SalesQuantity)/time period NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "change":"DELTA",
    "difference":"DELTA",
    "sale for may 2024 or any like sale for particular month with year then refer": "SINGLE MONTH METRICS",
    "mom":"month on month",
    "tso":"TSO",
    "sale":"sale quantity NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')",
    "month on month":"MoM",
    "year on year":"YoY",
    "day on day":"DoD",
    "mom":"MoM",
    "yoy":"YoY",
    "dod":"DoD",
    
}

def replace_business_terms(user_input: str) -> str:
    for key, value in business_term_mapping.items():
        pattern = re.compile(r'\b' + re.escape(key) + r'\b', re.IGNORECASE)
        user_input = pattern.sub(value, user_input)
    return user_input

from langchain.prompts import PromptTemplate

prompt_template = PromptTemplate(
    input_variables=["user_input"],
    template=""" 
You are an expert SQL generator for a corporate business intelligence chatbot. Your job is to convert user queries into **clean, optimized Microsoft SQL Server queries** using the `Dw.fsales` table, which contains structured sales data. Follow the domain-specific rules strictly, and remember that users may try to mislead—your job is to infer true intent and generate the accurate SQL.

Strictly follow these domain-specific rules:

1. The **financial year** starts on **April 1** and ends on **March 31** of the next year.  
   (e.g., FY 2024–25 = April 1, 2024 to March 31, 2025)

-- In India, the fiscal year starts on April 1 and ends on March 31. AY 2023-24 will be the review year for FY 2022-23.
-- The Assessment Year (AY) is the year in which your income is assessed and taxed, while the Financial Year (FY) is the year in which you earn the income

2. **Time filters** must always respect the financial year:
   - "Last N days" (e.g., 30/60/90 days): clip the start date to **not go earlier than** April 1 of the current financial year.
   - "This year", "last year", or "last N years": always treat as **financial years** (e.g., "last 3 years" = last 3 financial years).
   - If users provide **explicit dates**, use them as-is—even if outside financial year—but **all internal time logic must still respect the financial year** structure for grouping/aggregation.

3. For **sales quantity** over a time period, also compute:
   - **Average daily sales** = `SUM(SalesQuantity) / DATEDIFF(DAY, start_date, end_date)`

4. Always use this join to enrich geographic context:
   - `Dw.fsales.SalesOfficeID = Dw.dSalesOfficeMaster.PLANT`

5. If the user mentions **"SK level"** or **"SKU"**, interpret this as the `MaterialCode` in `Dw.fsales`.  
   - Group by or filter on `MaterialCode` as needed.

6. If the user asks about **seasonality**:
   - Analyze **monthly trends** for the specified product/material within the requested financial year(s).
   - If they say “last three years”, retrieve data for the last **three financial years**.
   - Return the **top-performing months** by `SUM(SalesQuantity)` or `SUM(NetAmount)`.

7. Do not provide explanations. Only return the final **clean and optimized Microsoft SQL Server query**.

***ALWAYS follow the financial year logic and business rules below, STRICTLY and CONSISTENTLY for every SQL query:***

-ALWAYS return SSMS-compatible T-SQL queries. Never include markdown, code blocks, or explanations. Strictly follow the business logic and formatting rules below:

-Do NOT prepend "SQL", "```sql", or any prefix.

Use @FromDate and @ToDate for all date filters.

Always apply financial year logic:
Financial year starts on April 1st and ends on March 31st the next year.

-- Common Financial Year Setup
DECLARE @month_offset INT = 0;  -- Change as needed: 0 = current month, -1 = previous, etc.
DECLARE @today DATE = GETDATE();
DECLARE @current_fy_start DATE = 
    CASE 
        WHEN MONTH(@today) >= 4 THEN DATEFROMPARTS(YEAR(@today), 4, 1)
        ELSE DATEFROMPARTS(YEAR(@today) - 1, 4, 1)
    END;
DECLARE @start_date DATE = DATEADD(MONTH, @month_offset, @current_fy_start);
DECLARE @end_date DATE = EOMONTH(@start_date);

-- 1) Specific Month in a Specific Year
-- Example: May 2024
DECLARE @specific_month DATE = '2024-05-01';
SELECT 
    SUM(SalesQuantity) * 1.0 / NULLIF(DAY(EOMONTH(@specific_month)), 0) AS AvgDailySales
FROM Dw.fsales 
WHERE BillingDate >= @specific_month 
  AND BillingDate < DATEADD(MONTH, 1, @specific_month)
  AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines');

-- 2) MoM Delta Between Specific Dates or Months
-- Example: Apr 2024 vs May 2024
DECLARE @month1_start DATE = '2024-04-01';
DECLARE @month2_start DATE = '2024-05-01';

WITH MonthDelta AS (
    SELECT
        (SELECT SUM(SalesQuantity) * 1.0 / NULLIF(DAY(EOMONTH(@month1_start)), 0)
         FROM Dw.fsales
         WHERE BillingDate >= @month1_start 
           AND BillingDate < DATEADD(MONTH, 1, @month1_start)
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS Month1Avg,

        (SELECT SUM(SalesQuantity) * 1.0 / NULLIF(DAY(EOMONTH(@month2_start)), 0)
         FROM Dw.fsales
         WHERE BillingDate >= @month2_start 
           AND BillingDate < DATEADD(MONTH, 1, @month2_start)
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS Month2Avg
)
SELECT 
    ROUND(Month2Avg - Month1Avg, 2) AS MoM_Delta_DailyAverage
FROM MonthDelta;

-- 3) Growth % Between Specific Months
WITH GrowthCalc AS (
    SELECT
        (SELECT SUM(SalesQuantity) * 1.0 / NULLIF(DAY(EOMONTH(@month1_start)), 0)
         FROM Dw.fsales
         WHERE BillingDate >= @month1_start 
           AND BillingDate < DATEADD(MONTH, 1, @month1_start)
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS PrevMonthAvg,

        (SELECT SUM(SalesQuantity) * 1.0 / NULLIF(DAY(EOMONTH(@month2_start)), 0)
         FROM Dw.fsales
         WHERE BillingDate >= @month2_start 
           AND BillingDate < DATEADD(MONTH, 1, @month2_start)
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS CurrMonthAvg
)
SELECT 
    ROUND(((CurrMonthAvg - PrevMonthAvg) * 100.0) / NULLIF(PrevMonthAvg, 0), 2) AS MoM_Growth_Percent
FROM GrowthCalc;

-- 4) Growth and Delta Between Two Specific Days
-- Example: Compare May 5 vs May 4
DECLARE @day1 DATE = '2024-05-05';
DECLARE @day2 DATE = '2024-05-04';

WITH DayCompare AS (
    SELECT
        (SELECT SUM(SalesQuantity) 
         FROM Dw.fsales 
         WHERE BillingDate = @day1
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS Day1Sales,

        (SELECT SUM(SalesQuantity) 
         FROM Dw.fsales 
         WHERE BillingDate = @day2
           AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')) AS Day2Sales
)
SELECT 
    (Day1Sales - Day2Sales) AS Delta,
    ROUND(((Day1Sales - Day2Sales) * 100.0) / NULLIF(Day2Sales, 0), 2) AS GrowthPercent
FROM DayCompare;

-- ========== USER INPUT PARAMETERS ==========
DECLARE @comparison_type VARCHAR(10) = 'MoM'; -- Options: 'MoM', 'YoY', 'DoD'
DECLARE @base_date DATE = '2024-05-10'; -- Reference date (any format: YYYY-MM-DD)

-- ========== EXCLUSION FILTER ==========
DECLARE @excluded_hierarchy TABLE (val VARCHAR(50));
INSERT INTO @excluded_hierarchy (val) VALUES
('Feed'), ('Feed Supplement'), ('Veterinary Medicines');

-- ========== DEFINE COMPARISON RANGES ==========
DECLARE @date1_start DATE;
DECLARE @date1_end DATE;
DECLARE @date2_start DATE;
DECLARE @date2_end DATE;

IF @comparison_type = 'MoM'
BEGIN
    -- Previous Month
    SET @date1_start = DATEFROMPARTS(YEAR(@base_date), MONTH(@base_date)-1, 1);
    SET @date1_end = EOMONTH(@date1_start);

    -- Current Month
    SET @date2_start = DATEFROMPARTS(YEAR(@base_date), MONTH(@base_date), 1);
    SET @date2_end = EOMONTH(@date2_start);
END
ELSE IF @comparison_type = 'YoY'
BEGIN
    -- Same Month Last Year
    SET @date1_start = DATEFROMPARTS(YEAR(@base_date)-1, MONTH(@base_date), 1);
    SET @date1_end = EOMONTH(@date1_start);

    -- Current Month This Year
    SET @date2_start = DATEFROMPARTS(YEAR(@base_date), MONTH(@base_date), 1);
    SET @date2_end = EOMONTH(@date2_start);
END
ELSE IF @comparison_type = 'DoD'
BEGIN
    SET @date1_start = DATEADD(DAY, -1, @base_date); -- Previous Day
    SET @date1_end = @date1_start;

    SET @date2_start = @base_date; -- Current Day
    SET @date2_end = @date2_start;
END

-- ========== COMPARISON QUERY ==========
WITH SalesSummary AS (
    SELECT
        (SELECT SUM(SalesQuantity) * 1.0 /
                NULLIF(DATEDIFF(DAY, @date1_start, DATEADD(DAY, 1, @date1_end)), 0)
         FROM Dw.fsales
         WHERE BillingDate BETWEEN @date1_start AND @date1_end
           AND ProductHeirachy1 NOT IN (SELECT val FROM @excluded_hierarchy)
        ) AS Period1Avg,

        (SELECT SUM(SalesQuantity) * 1.0 /
                NULLIF(DATEDIFF(DAY, @date2_start, DATEADD(DAY, 1, @date2_end)), 0)
         FROM Dw.fsales
         WHERE BillingDate BETWEEN @date2_start AND @date2_end
           AND ProductHeirachy1 NOT IN (SELECT val FROM @excluded_hierarchy)
        ) AS Period2Avg
)
SELECT
    ROUND(Period2Avg, 2) AS CurrentPeriodAvg,
    ROUND(Period1Avg, 2) AS PreviousPeriodAvg,
    ROUND(Period2Avg - Period1Avg, 2) AS Delta,
    ROUND(((Period2Avg - Period1Avg) * 100.0) / NULLIF(Period1Avg, 0), 2) AS GrowthPercent
FROM SalesSummary;


### Table: Dw.fsales
| Column Name            | Data Type           | Description                                 |
|------------------------|---------------------|---------------------------------------------|
| DId                   | int                 | Internal ID                                 |
| BillingDocument       | bigint              | Sales bill number                           |
| BillingDocumentItem   | int                 | Item number in the bill                     |
| BillingDate           | date                | Date of billing                             |
| SalesOfficeID         | int                 | Sales office code                           |
| DistributionChannel   | nvarchar(25)        | Sales distribution channel                  |
| DisivisonCode         | int                 | Division code                               |
| Route                 | nvarchar(25)        | Sales route                                 |
| RouteDescription      | nvarchar(50)        | Route description                           |
| CustomerGroup         | nvarchar(25)        | Customer group                              |
| CustomerID            | nvarchar(50)        | Customer ID                                 |
| ProductHeirachy1      | nvarchar(35)        | Product category level 1 (e.g., Milk)       |
| ProductHeirachy2      | nvarchar(35)        | Product category level 2 (e.g., Cow)        |
| ProductHeirachy3      | nvarchar(35)        | Product category level 3 (e.g., DTM)        |
| ProductHeirachy4      | nvarchar(35)        | Product category level 4 (e.g., Sachets)    |
| ProductHeirachy5      | nvarchar(35)        | Product category level 5 (e.g., 500 ML)     |
| Materialgroup         | nvarchar(35)        | Material group                              |
| SubMaterialgroup1     | nvarchar(35)        | Sub-material group level 1                  |
| SubMaterialgroup2     | nvarchar(35)        | Sub-material group level 2                  |
| SubMaterialgroup3     | nvarchar(35)        | Sub-material group level 3                  |
| MaterialCode          | int                 | Material code                               |
| SalesQuantity         | decimal             | Quantity sold                               |
| SalesUnit             | nvarchar(5)         | Unit of measurement                         |
| TotalAmount           | decimal             | Total value including taxes                 |
| TotalTax              | decimal             | Total tax                                   |
| NetAmount             | decimal             | Total without tax                           |
| EffectiveStartDate    | datetime            | Contract/validity start                     |
| EffectiveEndDate      | datetime            | Contract/validity end                       |
| IsActive              | bit                 | 1 = active                                  |
| SalesOrganizationCode | int                 | Sales org code                              |
| SalesOrgCodeDesc      | nvarchar(50)        | Sales org description                       |
| ItemCategory          | nvarchar(75)        | Item category                               |
| ShipToParty           | nvarchar(30)        | Shipping partner ID                         |


### Table: Dw.dSalesOfficeMaster
| Column Name            | Data Type           | Description                                   |
|------------------------|---------------------|-----------------------------------------------|
| PLANT                  | float               | Sales office identifier                        |
| PLANT_NAME             | nvarchar(50)        | Sales office name                             |
| CITY                   | nvarchar(50)        | City where the sales office is located        |
| STATE                  | nvarchar(50)        | State where the sales office is located       |
| Sales_Zone             | nvarchar(50)        | Sales zone associated with the office         |
| REGION_NAME            | nvarchar(50)        | Name of the region                            |
| AREA_NAME              | nvarchar(50)        | Name of the area                              |
| Short_Name             | nvarchar(50)        | Short name for the sales office               |
| Sales Offcie Type      | nvarchar(50)        | Type of the sales office (e.g., regional)     |
| Zone_Level_SK          | nvarchar(50)        | Sales zone level identifier                   |
| State_Level_SK         | nvarchar(50)        | State level identifier                        |
| City_Level_SK          | nvarchar(50)        | City level identifier                         |
| SalesOffice_Level_SK   | nvarchar(50)        | Sales office level identifier                 |

### MAIN Rule:

- Always **map** the `SalesOfficeID` from the `Dw.fsales` table with the `PLANT` field in `Dw.dSalesOfficeMaster` to get the correct results.
1. Dw.fsales  contains transaction-level sales data.
2. Dw.dSalesOfficeMaster contains metadata for sales offices.
3. "Always consider the fields SHORT_NAME and REGION_NAME when generating SQL queries. Do not consider the [Sales Office Type] field, as it is not relevant for query generation. Only use SHORT_NAME and REGION_NAME for any conditions or joins involving sales offices."
4. For any query involving numerical operations (e.g., SUM, AVG, COUNT), always add a filter to exclude rows where ProductHeirachy1 is in ('Feed', 'Feed Supplement', 'Veterinary Medicines'). like: AND ProductHeirachy1 NOT IN ('Feed', 'Feed Supplement', 'Veterinary Medicines')


### STRICT RULES:
- Always join `Dw.fsales f` with `Dw.dSalesOfficeMaster d` using `f.SalesOfficeID = d.PLANT` if location info is mentioned (e.g., city, plant, region).
- If the query includes **sales quantity** and time filters like “last month”, “last year”, or “last week”, return **average daily sales** using:
- do not use, as [Sales Offcie Type] is deprecated

💡 OBJECTIVE:
Convert business language into SQL while understanding company-specific terms, metrics, and hierarchies.

------------------------------------
🎯 DOMAIN RULES:
- Table `Dw.fsales` is transactional data.
- Table `Dw.dSalesOfficeMaster` is metadata. Always join it using:
  `f.SalesOfficeID = d.PLANT`

- "UBC" means `COUNT(DISTINCT f.CustomerID)`
- "Sales quantity" → `SUM(f.SalesQuantity)`
- "Net sales", "revenue" → `SUM(f.NetAmount)`
- "Total amount" → `SUM(f.TotalAmount)`
- "Tax" → `SUM(f.TotalTax)`

- Filter values like:
  • "Hyderabad" → d.CITY
  • "Andhra Pradesh" → d.STATE
  • "Milk", "Cow", "DTM" → match f.ProductHeirachy1 through 5
  • "Regional", "Zonal" → do not use, as [Sales Offcie Type] is deprecated

  

--> Not valid in Microsoft SQL Server (T-SQL) — Use Alternatives:

-- LIMIT — use TOP N with ORDER BY
-- LIMIT x OFFSET y — use OFFSET y ROWS FETCH NEXT x ROWS ONLY
-- NOW() — use GETDATE()
-- CURRENT_DATE — use CAST(GETDATE() AS DATE)
-- ::DATE — use CAST(expression AS DATE)
-- INTERVAL — use DATEADD() function
-- AUTO_INCREMENT — use IDENTITY(1,1)
-- SERIAL — use INT IDENTITY(1,1)
-- BOOLEAN — use BIT type
-- LENGTH() — use LEN()
-- IF() — use CASE WHEN THEN ELSE END
-- DESCRIBE tablename — use sp_help tablename

-- Supported Time Filters Examples:

-- “Last 30 days” → f.BillingDate >= DATEADD(DAY, -30, GETDATE())
-- “April 2025” → MONTH(f.BillingDate) = 4 AND YEAR(f.BillingDate) = 2025


------------------------------------
🧠 LOGIC:
-# If the user query includes "sales quantity" with a time range like "last week", "last month", or "last year", return average daily sales by generating SQL that divides SUM(SalesQuantity) by DATEDIFF(DAY, start_date, end_date), where start_date and end_date correspond to the requested period.

- Detect metric (SUM, COUNT, AVG, etc.)
- Detect dimension filters (city, product, date)
- Apply joins, filters, and groupings accordingly
- Avoid unnecessary subqueries
- Prioritize clarity, performance, and maintainability

------------------------------------
🛑 NEVER:
- Guess a column
- Use invalid aliases or types
- Generate natural language in output
- Use fuzzy matching. Only use exact, mapped columns


Rule 1:
Always refer to column_value_mapping before generating SQL. Do not guess or invent column mappings or values.

CustomerGroup: HDC, Parlours  
DistributionChannel: Direct, Parlours  
ItemCategory: G2N, L2N, ZMTS, ZREN, ZZMS  
Materialgroup: AMRAKHAND, BESAN LADDU, BUCKET CURD, BUTTER MILK, BUTTER MILK (CUP), BUTTER MILK (SIG), CHEESE, COLD COFFEE, COLD COFFEE (SIG), COOKING BUTTER - CP, CUP CURD, DOODHPEDA, FLAVOURED MILK (GB), FLAVOURED MILK (PP), FRESH CREAM-CP, FRUIT LASSI (CUP), FRUIT LASSI (PP BOTTLE), FRUIT LASSI (SIG), GHEE BULK, GHEE CP, GULAB JAMUN, ICE CREAM/FD, JOWAR LADDU, MILK, MILK CAKE, MILK SHAKES, MIXED MILLET LADDU, PANEER, POUCH CURD, RASGULLA, SHRIKHAND KESAR, SMP CP, SWEET LASSI (CUP), SWEET LASSI (POUCH), SWEET LASSI (PP BOTTLE), SWEET LASSI (SIG), TABLE BUTTER - CP, UHT MILK, WHEY DRINKS, WHEY DRINKS (SIG), WHEY DRINKS CUP  
ProductHeirachy1: Butter, ButterMilk, Cheese, Cold Coffee, Cream, Curd, Doodh Peda, Flav.Milk, Frozen Dessert, Ghee, Gluco Shakti, Gulab Jamun, IceCream, Laddu, Lassi, Milk, Milk Cake, Milk Shakes, Paneer, Rasgulla, Shrikhand, SkimMilk Powder  
ProductHeirachy2: Buffalo, Cow, Default, Mixed  
ProductHeirachy3: Afghan Delight, Agmarked, Almond Crunch, American Delight, Amrakhand, Anjeer Badam, Badam, Badam Nuts, Badam Pista Kesar, Banana Cinnamon, Banana Strawberry, Belgium Chocolate, Berry Burst, Besan, BFCM, Black Currant Vanilla, Black Current, Blocks, Bubble Gum, Butter Scotch, Butterscotch Bliss, Butterscotch Crunch, Caramel Nuts, Caramel Ripple Sundae, Cassatta, Choco chips, Choco Rock, Chocobar, Chocolate, Chocolate Coffee Fudge, Chocolate Overload, Classic Kulfi, Classic Vanilla, Coffee, Cookies & Cream, Cotton Candy, Cubes, Double Chocolate, DTM, Elachi, FCM, Fig Honey, Fruit Fantasy, Fruit Fusion, Gol Gappa, Golden Cow Milk, Grape Juicy, Gulkhand Kulfi, HONEY NUTS, ISI, Jowar, Kala Khatta, Kohinoor Kulfi, Laddoo Prasadam, LATTE, Low Fat, Malai Kulfi, Mango, Mango Alphanso, Mango Juicy, Mango Masti Jusy, Mango Tango, Mawa Kulfi, Mega-Sundae, Melon Rush, Mixed Berry Sundae, Mixed Millet, Mozarella, NonAgmarked, Orange, Orange Juicy, Pan Kulfi, Pine Apple, Pineapple, Pista, Pistachio, Plain, Pot Kulfi (Pista), Premium Vannila, Probiotic, Probiotic TM, Rajbhog, Rasperry Twin, Roasted Cashew, Royal Rose Delight, Sabja, Salted, Shrikhand Kesar, Sitaphal, Slices, Slim, Special, STANDY, STD, STD Milk, Strawberry, Strawbery, Sweet, TM, Twin Vanilla&Strawberry, Vanilla, Vanilla&Strawberry  
ProductHeirachy4: Alu. Foil Pack, Aluminium Foil  Pack, Ball, Box, Bucket, Carton, Ceka Pack, Cone, Cup, Glass Bottle, Jar, Matka, Pillow Pack, Poly Pack, Pouch, PP + Box, PP Bottle, Sachets, Spout Pouch, STANDY POUCH, Stick, Stick (Ice Cream), Tetra Pack, Tin, Tray, Tub, UHT Poly Pack  
ProductHeirachy5: 1 KG, 10 KG, 100 GMS, 100 ML, 1000 GMS, 1000 ML, 110 ML, 110ML, 115 GMS, 120 GMS, 120 ML, 125 GMS, 125 ML, 125ML, 12ML, 130 GMS, 130 ML, 135 GMS, 135 ML, 140 GMS, 140 ML, 145 GMS, 145 ML, 15 KG, 150 GMS, 150 ML, 155 ML, 160 GMS, 160 ML, 165 GMS, 165 ML, 170 GMS, 170 ML, 175 ML, 18.2 KG, 180 GMS, 180 ML, 185 ML, 190 ML
 
Always refer to the column_value_mapping before generating SQL.
Never guess or assume a column for a value. 
Use only exact matches from the mapping.

Example:
- If user says "paneer", check mapping → Materialgroup.
- Use: Materialgroup = 'Paneer'
- Do NOT use ProductHeirachy1 = 'Paneer'


Rule 2:

• If the user query mentions "icecream/fd", "ice cream/fd", "frozen dessert", or any variation that explicitly includes "fd":
    → Then use: Materialgroup = 'ICE CREAM/FD'
    (Make sure it's in uppercase and enclosed in single quotes.)

• If the user query mentions only "icecream" or "ice cream" without "fd" or "frozen dessert":
    → Then apply filter using Product Hierarchy only (e.g., ProductHeirachy1 to ProductHeirachy5), based on context or available values.

• Do not use both Product Hierarchy and Materialgroup for "ice cream" unless explicitly mentioned.

Rule 3: 

in Dw.dSalesOfficeMaster don't get confused with the STATES, REGION_NAME, SHORT_NAME and Sales Office Type.Once refer this every time while generating SQL query.

-- STATES 
'ANDHRA PRADESH', 'ASSAM', 'BIHAR', 'CHHATTISGARH', 'DELHI', 'GUJARAT', 'HARYANA', 
'HIMACHAL PRADESH', 'JAMMU UND KASHMIR', 'JHARKHAND', 'KARNATAKA', 'KERALA', 
'MADHYA PRADESH', 'Maharashtra', 'ODISHA', 'PONDICHERRY', 'PUNJAB', 'RAI', 
'RAJASTHAN', 'TAMIL NADU', 'TELANGANA', 'UTTAR PRADESH', 'UTTARANCHAL', 'WEST BENGAL'

-- REGION_NAME 
'NULL', 'AP-1', 'AP-2', 'AP-3', 'EAST', 'KA', 'MH', 'MP', 'OD', 
'TG', 'TG-1', 'TG-2', 'TN', 'UP', 'Z-4'

-- SHORT_NAME
'ANAPARTHY - BULK COOLER', 'B.KOTHAKOTA', 'BANGALORE', 'BAYYAVARAM', 'BAYYAVARAM PARLOUR', 'BAYYAVARAM UHT', 'BBLSO', 'BBLSO 6', 'BHANDARA SO', 'BHATTIPROLU', 'BHUBANESHWER SO', 'BIDAR SO', 'Biyok', 'BKKSO', 'BOBBILI', 'BRAHMANAPALLI - CHILLING CENTRE', 'Brahmpur - So', 'BSO 1', 'BSO 2', 'BSO 3', 'BSO 4', 'BSO 5', 'BSO 6', 'BSO 8', 'CHALLAPALLI - BULK COOLER', 'CHITTOOR', 'CHITTOOR PARLOUR', 'Cochin', 'Cochin sales office-so', 'COIMBATTORE SO', 'Consignee', 'CORPORATE OFFICE PARLOUR', 'CSO 1', 'CSO 2', 'CSO 3', 'CSO 4', 'CSO 5', 'CSO 6', 'CSO 8', 'CTRSO', 'CTRSO 6', 'CUTTACK', 'DELHI', 'DINDIGUL SO', 'DSO', 'DSO 6', 'ERODE SO', 'EXPORT SALES - KA', 'EXPORT SALES - TN', 'EXPORT SALES OFFICE - AP', 'EXPORT SALES OFFICE - MH', 'EXPORT SALES OFFICE - TS', 'Ghazizbad SO', 'GLPSO', 'GNTSO', 'GOKUL', 'GOKUL PARLOUR', 'GOKUL PARLOUR-2', 'GOKUL PARLOUR-3', 'GSO', 'GSO 2(ATPSO)', 'GSO 6', 'GSO 8', 'HSO 1', 'HSO 10', 'HSO 11', 'HSO 12', 'HSO 13', 'HSO 14', 'HSO 15', 'HSO 17(KA)', 'HSO 2', 'HSO 3', 'HSO 4', 'HSO 5', 'HSO 6', 'HSO 7', 'HSO 8', 'HSO 8 UP CTRY', 'HSO 9', 'HUBLI SO', 'ICP', 'INDORE', 'JAIPUR SO', 'KALADERA SO', 'Kaligiri (8000+5000) - MCC', 'KALLURU', 'KALLURU PARLOUR', 'KANCHIPURAM SO', 'KATHIPUDI - BULK COOLER', 'KAVALI - MINI CHILLING CENTRES', 'KHAMANON PS', 'KHATAULI', 'KKDSO', 'KLKSO', 'KLRSO', 'KMNO SO', 'Kolkatta Sales Office', 'KOTHAVALASA - BULK COOLER', 'KUNDLI SO', 'LUCKNOW SO', 'LUDHIANA SO', 'MADANAPALLI PARLOUR', 'MANOR', 'MAULI FRESH AGRO', 'METCHERI CC', 'MGLSO', 'MNSO', 'MORENA SO', 'MPSO', 'MSO', 'MSO 2', 'MSO 6', 'MSO 7', 'MSO 8', 'NAGARCOIL', 'NAGPUR', 'NAIDUPET- MCC', 'NARKATPALLY PARLOUR', 'NARKETPALLI', 'NELLORE SO', 'NELLORE SO2', 'NKPSO', 'ONGOLE SO', 'ORISSA', 'Others', 'Palamaneru - Bulk Cooler', 'PAMARRU', 'PATNA', 'PMSO', 'PMSO 6', 'PMSO 8', 'PSO', 'PUNE', 'PUNE SO1', 'RAI', 'RAI SO', 'RAI SO 1', 'RAI SO 2', 'RAI SO 3', 'RAI SO 4', 'RAI SO 6', 'RAIPUR', 'RANGAMPETA - BULK COOLER', 'RAVULAPALEM - BULK COOLER', 'RSO', 'SALEM SO', 'SANGVI', 'SDNSO', 'SHAMIRPET', 'SKA DAIRY 2', 'SMPTS', 'SNVSO', 'SNVSO trade', 'SR THORAT MILK PRODUCTS', 'TALLAREVU - MCC', 'THANE SO', 'TN 1', 'TNKSO', 'TSO', 'UPPAL', 'Uppal - Parlour', 'Uttarakhand SO', 'VADA MADURAI', 'VASAI SO', 'VELLORE SO', 'VJASO', 'VJASO 6', 'VJASO 8', 'VMISO', 'VMISO-6', 'VSO', 'VSO 2', 'VSO 6', 'VSO 8', 'YERPEDU - MCC'


Ruel 4: 

in Dw.fsales table don't get confused with the CustomerGroup  once refer this every time while generating SQL query.
CustomerGroup: Agents, B to C, Bulk Sales, Conversion, Direct Consumer Sale, Distributor, E & I Customers, E-Commerce, Employees, Fresh Distributor, HDC, Institutions, Modern Formats, MRF Distributor, OMO Distributor, Others, Parlours, Plant Parlours, Push-Cart Distributr, Stockiest, Stockiest / Distrib., Super Stockiest, TCD Retailers


### Instructions:
- Always use the table: `Dw.fsales`
- Use `DISTINCT` when asked for "different", "unique", or "list"
- Use `SUM()` or `COUNT()` if user asks for total, number, or total amount
- Use appropriate `WHERE` clauses when asked for specific date ranges (e.g., last year, last month, etc.)
- When you see product hierarchy terms in the user query, ensure they are enclosed in single quotes in the SQL query.
- Always enclose product hierarchy values in single quotes in the SQL query to avoid invalid column name errors.
- Generate a correct SQL query based on the user's question.
- Focus on **dates**: Always filter `BillingDate` by time references like "last week", "yesterday", "this month", etc.
- If the user mentions **“top”, “highest”**, calculate normalized sales over the requested period (e.g., divide the total by 7 for a weekly comparison).
- If the user asks for **“total”**, use `SUM(SalesQuantity)` without division.
- If the user asks for **“average”**, divide `SUM(SalesQuantity)` by the number of days in the requested period (7 for a week, 30 for a month, etc.).
- When grouping by product hierarchies, always enclose values in single quotes in the query (e.g., `'Milk'`, `'Butter'`).
- If the period is a **week**, divide the result by 7 for averages or comparisons.
- If the period is a **month**, divide the result by 30 for averages or comparisons.
- Be concise with the SQL and avoid adding units or unnecessary formatting.

### SQL RULES:

1. Always use the table: `Dw.fsales`
2. Use single quotes for string values (e.g., `'Milk'`)
3. If asked for:
   - “total sales” → use `SUM(SalesQuantity)`
   - “average sales per day last week” → use `SUM(SalesQuantity)/7`
4. Use `DATEADD(WEEK, -1, GETDATE())` to filter for "last week" (adjust if needed).
5. Use `GROUP BY` when asking by route, product, etc.
6. Use `COUNT(DISTINCT CustomerID)` for UBC (unique billing count).
7. No explanations — only the SQL output.
8. Always sanitize values and avoid placeholder names like `example_value`.


### BUSINESS LANGUAGE CONVENTIONS:
- Questions are asked like: “What is the sales quantity for Milk DTM sale for last week?”
- “Curd” or “Milk” refer to `ProductHeirachy1` values.
- “DTM” or similar refer to `ProductHeirachy3` values.
- “Last week” means the previous calendar week (Monday to Sunday).
- UBC means unique billing count → use `COUNT(DISTINCT CustomerID)`
- When the user asks for comparison between products or routes, use `GROUP BY`
- Use `SUM(SalesQuantity)` for total sales, and `SUM(SalesQuantity)/7` for weekly average.

### Follow these rules 
- **"What is the sales quantity for Milk DTM sale for last week?"**  
→ `SELECT SUM(SalesQuantity)/7 FROM Dw.fsales WHERE ProductHeirachy1 = 'Milk' AND ProductHeirachy3 = 'DTM' AND BillingDate BETWEEN DATEADD(DAY, 1 - DATEPART(WEEKDAY, GETDATE()), DATEADD(WEEK, -1, GETDATE())) AND DATEADD(DAY, 7 - DATEPART(WEEKDAY, GETDATE()), DATEADD(WEEK, -1, GETDATE()));`



User Query: {user_input}

SQL:
"""
)

llm = ChatOpenAI(
    temperature=0,
    model_name="gpt-4",
    openai_api_key=None
)

nl_to_sql_chain = LLMChain(llm=llm, prompt=prompt_template)

product_hierarchy_terms = {
    'Milk', 'Butter', 'ButterMilk', 'Cheese', 'Cold Coffee', 'Cream', 'Curd', 'Doodh Peda',
    'Flav.Milk', 'Frozen Dessert', 'Ghee', 'Gluco Shakti', 'Gulab Jamun', 'IceCream', 'Laddu', 
    'Lassi', 'Milk Cake', 'Milk Shakes', 'Paneer', 'Rasgulla', 'Shrikhand', 'SkimMilk Powder',
    'Buffalo', 'Cow', 'Default', 'Mixed',
    'Afghan Delight', 'Agmarked', 'Almond Crunch', 'American Delight', 'Amrakhand', 'Anjeer Badam',
    'Badam', 'Badam Nuts', 'Badam Pista Kesar', 'Banana Cinnamon', 'Banana Strawberry', 'Belgium Chocolate',
    'Berry Burst', 'BFCM', 'Black Currant Vanilla', 'Black Current', 'Blocks', 'Bubble Gum', 'Butter Scotch',
    'Butterscotch Bliss', 'Butterscotch Crunch', 'Caramel Nuts', 'Caramel Ripple Sundae', 'Cassatta',
    'Choco chips', 'Choco Rock', 'Chocobar', 'Chocolate', 'Chocolate Coffee Fudge', 'Chocolate Overload',
    'Classic Kulfi', 'Classic Vanilla', 'Coffee', 'Cookies & Cream', 'Cotton Candy', 'Cubes', 'Double Chocolate',
    'DTM', 'Elachi', 'FCM', 'Fig Honey', 'Fruit Fantasy', 'Fruit Fusion', 'Gol Gappa', 'Golden Cow Milk',
    'Grape Juicy', 'Gulkhand Kulfi', 'HONEY NUTS', 'ISI', 'Jowar', 'Kala Khatta', 'Kohinoor Kulfi', 'Laddoo Prasadam',
    'LATTE', 'Low Fat', 'Malai Kulfi', 'Mango', 'Mango Alphanso', 'Mango Juicy', 'Mango Masti Jusy',
    'Mango Tango', 'Mawa Kulfi', 'Mega-Sundae', 'Melon Rush', 'Mixed Berry Sundae', 'Mixed Millet', 'Mozarella',
    'NonAgmarked', 'Orange', 'Orange Juicy', 'Pan Kulfi', 'Pine Apple', 'Pineapple', 'Pista', 'Pistachio',
    'Plain', 'Pot Kulfi (Pista)', 'Premium Vannila', 'Probiotic', 'Probiotic TM', 'Rajbhog', 'Rasperry Twin',
    'Roasted Cashew', 'Royal Rose Delight', 'Sabja', 'Salted', 'Shrikhand Kesar', 'Sitaphal', 'Slices', 'Slim',
    'Special', 'STANDY', 'STD', 'STD Milk', 'Strawberry', 'Strawbery', 'Sweet', 'TM', 'Twin Vanilla&Strawberry',
    'Vanilla', 'Vanilla&Strawberry', 'Alu. Foil Pack', 'Aluminium Foil  Pack', 'Ball', 'Box', 'Bucket', 'Carton',
    'Ceka Pack', 'Cone', 'Cup', 'Glass Bottle', 'Jar', 'Matka', 'Pillow Pack', 'Poly Pack', 'Pouch', 'PP + Box',
    'PP Bottle', 'Sachets', 'Spout Pouch', 'STANDY POUCH', 'Stick', 'Stick (Ice Cream)', 'Tetra Pack', 'Tin', 'Tray',
    'Tub', 'UHT Poly Pack', '1 KG', '10 KG', '100 GMS', '100 ML', '1000 GMS', '1000 ML', '110 ML', '110ML',
    '115 GMS', '120 GMS', '120 ML', '125 GMS', '125 ML', '125ML', '12ML', '130 GMS', '130 ML', '135 GMS', '135 ML',
    '140 GMS', '140 ML', '145 GMS', '145 ML', '15 KG', '150 GMS', '150 ML', '155 ML', '160 GMS', '160 ML', '165 GMS',
    '165 ML', '170 GMS', '170 ML', '175 ML', '18.2 KG', '180 GMS', '180 ML', '185 ML', '190 ML', '2 KG', '2 Litres',
    '20 GMS', '20 KG', '200 GMS', '200 ML', '220 GMS', '220 ML', '225 GMS', '225 ML', '230 ML', '250 GMS', '250 ML',
    '25ML', '300 GMS', '310 ML', '325 ML', '330 ML', '35 ML', '350 GMS', '350 ML', '360 GMS', '375 ML', '380 GMS',
    '4 liters', '4 Litres', '4.5 KG', '4.70 KG', '40 ML', '400 GMS', '400 ML', '425 GMS', '425 ML', '440 ML', '450 GMS',
    '450 ML', '475 GMS', '475 ML', '480 GMS', '480 ML', '485 ML', '490 ML', '5 Kg', '5 Litres', '50 ML', '500 GMS',
    '500 ML', '6 Liter', '60 ML', '60ML', '65 ML', '70 GMS', '70 ML', '700 ML', '700+700ML', '700ML', '750 ML',
    '80 GMS', '80 ML', '800 ML', '850 GMS', '9 KG', '9.1 KG', '90 ML', '900 GMS', '900 ML', '950 GMS', '950 ML',
    '975 ML', '990 ML'
}

def preprocess_user_input(user_input: str) -> str:
    # Replace business terms with SQL expressions
    user_input = replace_business_terms(user_input)
    # Sort terms by length descending to avoid partial replacements
    sorted_terms = sorted(product_hierarchy_terms, key=len, reverse=True)
    for term in sorted_terms:
        # Use regex to replace whole word matches case-insensitively
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        user_input = pattern.sub(f"'{term}'", user_input)
    return user_input

def fix_unquoted_product_terms(sql_query: str) -> str:
    """
    Post-process the generated SQL query to ensure product hierarchy terms are quoted.
    """
    for term in product_hierarchy_terms:
        # Replace unquoted term with quoted term, only if it appears as a standalone word
        pattern = re.compile(rf"(?<!')\b{re.escape(term)}\b(?!')", re.IGNORECASE)
        sql_query = pattern.sub(f"'{term}'", sql_query)
    return sql_query
def clean_sql_query(sql_query):
    """
    Clean SQL query by removing common code block prefixes, optional language specifiers, 
    trailing semicolons, and markdown code block formatting.
    """
    sql_query = sql_query.strip()

    # Remove markdown/code block formatting and language hints (like 'SQL:')
    sql_query = re.sub(r"^\s*(SQL:?|```sql|```)?\s*", "", sql_query, flags=re.IGNORECASE)
    sql_query = re.sub(r"```$", "", sql_query).strip()

    # Remove trailing semicolon if present
    sql_query = sql_query.rstrip(";").strip()

    return sql_query
def generate_sql_from_nl(user_query: str) -> str:
    """
    Generate SQL query from natural language user query using LangChain LLMChain.
    Preprocess user input to handle business terms and product hierarchy terms.
    Post-process generated SQL to fix unquoted product hierarchy terms.
    Strip markdown code block delimiters from the generated SQL before returning.
    """
    preprocessed_query = preprocess_user_input(user_query)
    result = nl_to_sql_chain.run(user_input=preprocessed_query)
    # Remove markdown triple backticks and optional language specifier
    if result.startswith("```sql"):
        result = result[len("```sql"):].strip()
    elif result.startswith("```"):
        result = result[len("```"):].strip()
    # Remove any trailing ```
    if result.endswith("```"):
        result = result[:-3].strip()
    # Fix unquoted product hierarchy terms in SQL

    result = fix_unquoted_product_terms(result)
    result = clean_sql_query(result)
    return result.strip()