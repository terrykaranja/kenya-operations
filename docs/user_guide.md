# User Guide - SEZ Ledger Automation Tool

## Getting Started

### First Login
1. Open the application in your browser (default: http://localhost:5173)
2. Sign in with your credentials (provided by admin)
3. You'll land on the Dashboard

### Dashboard
The dashboard shows:
- **Import Lines**: Total number of import records
- **Export Lines**: Total number of export records
- **Open Balances**: Import lines that still have remaining quantity
- **Documents**: Total uploaded PDF documents
- Quick action buttons for Upload Import/Export
- Recent activity feed

---

## Importing Goods

### Step 1: Upload Import PDF
1. Click **Upload Import** from the Dashboard
2. Drag & drop your import customs PDF, or click "Choose File"
3. Click **Upload PDF**

### Step 2: Extract Data
- Click **Extract with AI** to use Claude to read the document
- For testing, click **Use Mock Data** to see example data

### Step 3: Review Extracted Data
- All extracted fields are shown in an editable form
- Fields are highlighted by confidence:
  - No highlight = High confidence (80%+)
  - Yellow ring = Medium confidence (50-80%)
  - Red ring = Low confidence (below 50%)
- Hover over any field to see the source text
- Edit any field to correct extraction errors
- Click **+ Add Item** to add additional line items
- Click **Remove** to delete a line item

### Step 4: Confirm
- Click **Confirm** to save the import entries to the database
- Initial balances are set to the full imported quantities

---

## Exporting Goods

### Step 1: Upload Export PDF
1. Click **Upload Export** from the Dashboard
2. Upload the export customs PDF

### Step 2: Extract & Review
- Same extraction and review process as imports

### Step 3: Match to Import Lines
- For each export item, click **Find Matches** to find candidate import lines
- Candidates are filtered by positive remaining balance
- Select the import line this export draws from
- Prorated values are automatically calculated:
  - `Customs Value = Import Customs Value x (Qty Exported / Qty Imported)`
  - `BIF Value = Import BIF Value x (Qty Exported / Qty Imported)`

### Step 4: Confirm
- Click **Confirm** to save exports and update import balances
- If export exceeds remaining balance, you'll see an overdraft warning
- Admin users can override with a mandatory reason

---

## Searching the Ledger

1. Navigate to **Search** from the top navigation
2. Enter search criteria:
   - Entry Number
   - File Number
   - Description (partial match)
   - Consignor (partial match)
   - HS Code (exact match)
   - Country
   - Open balance only (checkbox)
3. Click **Search** or press Enter
4. Click any result row to see full details including export history
5. From the detail view, admin users can delete export lines (restores balance)

---

## Downloading the Ledger

1. Navigate to **Download**
2. Choose output style:
   - **Blank continuation rows** (legacy format): Leaves consignor/file/date/entry blank on continuation items
   - **Fully populated rows**: Every column filled on every row
3. Click **Download Excel** to generate and download the formatted .xlsx file

---

## Legacy Data Import (Admin Only)

1. Navigate to **Download**
2. Click **Import Legacy Data** to import from `Seza_Stock_Ledger_Hackathon.xlsx`
3. This creates all import and export records from the original Excel file
4. Can only be run once (prevents duplicates)

---

## Audit Log

1. Navigate to **Audit Log**
2. Filter by Entity Type (Import Line, Export Line, User, etc.)
3. Filter by Change Type (Create, Update, Delete, Override)
4. All changes are logged with:
   - Timestamp
   - Who made the change
   - What was changed (old and new values)
   - Source (auto-extracted, human-corrected, system)
5. Admin users can **Export CSV** for compliance records

---

## Admin Panel (Admin Only)

### User Management
- Create new users with username/password
- Toggle admin privileges
- Activate/deactivate users
- Delete users (cannot delete yourself)

### Units Management
- Add allowed unit codes (e.g., KG, UNT)
- Used for validation and dropdowns

### Countries Management
- Add allowed country codes (ISO 3166-1 alpha-2)
- Used for validation and dropdowns

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Not authenticated" | Your session expired. Sign in again |
| "ANTHROPIC_API_KEY not configured" | Set the API key in `.env` file |
| Extraction returns wrong data | Review and correct in the review screen |
| "Exceeds remaining balance" | Use admin override or check the correct import line |
| Download generates empty file | Run Legacy Data Import first |
