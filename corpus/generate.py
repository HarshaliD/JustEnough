"""
corpus/generate.py: Deterministic generator for the JustEnough Day 1 synthetic corpus.
Frozen seed: 20261009 (registered in DAY1_SPEC.md).

Generates 10 text documents:
  - BS-1..3: Bank statements
  - CC-1..2: Credit-card statements
  - PS-1..2: Payslips / Form 16
  - RA-1: Rent agreement
  - UB-1: Utility bill
  - IL-1: Insurance / clinical lab document

Records every planted sensitive item in corpus/planted.json with exact (doc_id, category, location).
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_SEED = 20261009
CORPUS_DIR = Path(__file__).resolve().parent
PLANTED_JSON_PATH = CORPUS_DIR / "planted.json"


@dataclass(frozen=True)
class PlantedItem:
    id: str
    doc_id: str
    category: str
    value: str
    location: Dict[str, Any]  # {"line": int, "start_char": int, "end_char": int}


class DocumentBuilder:
    """Helper to assemble a document line by line while tracking exact character offsets."""

    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.lines: List[str] = []
        self.planted_items: List[PlantedItem] = []
        self._item_counter = 0

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    def add_planted_field(self, line_prefix: str, category: str, value: str, line_suffix: str = "") -> None:
        """Appends a line containing a planted field and registers its exact location."""
        self._item_counter += 1
        item_id = f"{self.doc_id}-{self._item_counter:02d}"

        # Current text before this line
        current_text = "\n".join(self.lines)
        if self.lines:
            line_start_char = len(current_text) + 1  # accounting for newline
        else:
            line_start_char = 0

        line_text = f"{line_prefix}{value}{line_suffix}"
        val_start_char = line_start_char + len(line_prefix)
        val_end_char = val_start_char + len(value)
        line_number = len(self.lines) + 1  # 1-indexed

        self.planted_items.append(
            PlantedItem(
                id=item_id,
                doc_id=self.doc_id,
                category=category,
                value=value,
                location={
                    "line": line_number,
                    "start_char": val_start_char,
                    "end_char": val_end_char,
                },
            )
        )
        self.lines.append(line_text)

    def build(self) -> Tuple[str, List[PlantedItem]]:
        content = "\n".join(self.lines) + "\n"
        return content, self.planted_items


def build_bs1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("BS-1")
    builder.add_line("================================================================================")
    builder.add_line("                       STATE BANK OF INDIA - ACCOUNT STATEMENT                  ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Account Holder Name: ", "person_name", "Aarav Sharma")
    builder.add_planted_field("Account Number:      ", "account_identifier", "30981245781")
    builder.add_planted_field("Customer CIF:        ", "internal_id", "CIF88392014")
    builder.add_planted_field("Registered Mobile:   ", "contact", "+91-9845012345")
    builder.add_planted_field("Communication Addr:  ", "address", "Flat 402 Shanti Vihar Indiranagar Bengaluru 560038")
    builder.add_line("Branch:              Indiranagar Branch | IFSC: SBIN0004521")
    builder.add_line("Statement Period:    01-Sep-2026 to 15-Sep-2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Date         Description                        Debit (INR)   Credit (INR)    Balance (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("", "transaction_date", "2026-09-02", "   UPI/aarav@okaxis/OPENING_BALANCE               -              -        85000.00")
    builder.add_planted_field("2026-09-03   UPI/Swiggy Bangalore/food           ", "amount", "450.00", "              -        84550.00")
    builder.add_line("             Merchant: Swiggy Bangalore")
    builder.add_planted_field("2026-09-05   UPI-TRANSFER to ", "counterparty_name", "Priya Patel", "                   1200.00              -        83350.00")
    builder.add_line("             Narration: UPI/priya@okicici/dinner_split")
    builder.add_planted_field("2026-09-08   POS/Merchant: ", "merchant", "Apollo Pharmacy Indiranagar", "       620.00              -        82730.00")
    builder.add_planted_field("2026-09-12   Closing Statement Balance:                                              ", "balance", "82730.00")
    builder.add_line("================================================================================")
    builder.add_line("END OF STATEMENT - This is a computer generated document and requires no signature.")
    return builder.build()


def build_bs2(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("BS-2")
    builder.add_line("================================================================================")
    builder.add_line("                           HDFC BANK - SAVINGS ACCOUNT STATEMENT                ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Customer Name:       ", "person_name", "Vikram Malhotra")
    builder.add_planted_field("Savings Account No:  ", "account_identifier", "50100432891234")
    builder.add_planted_field("Customer ID:         ", "internal_id", "CUST91028345")
    builder.add_planted_field("Registered Contact:  ", "contact", "+91-9811234567")
    builder.add_planted_field("Mailing Address:     ", "address", "A-12 Sector 62 Noida Uttar Pradesh 201309")
    builder.add_line("Branch:              Noida Sector 62 | IFSC: HDFC0001204")
    builder.add_line("Period:              01-Sep-2026 to 15-Sep-2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Date         Description                        Debit (INR)   Credit (INR)    Balance (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("", "transaction_date", "2026-09-01", "   OPENING BALANCE FOR SEPTEMBER                  -              -       145000.00")
    builder.add_planted_field("2026-09-04   UPI payment to ", "counterparty_name", "Rohan Verma", "                    2500.00              -       142500.00")
    builder.add_line("             UPI Reference: rohan.verma@okhdfcbank")
    builder.add_planted_field("2026-09-07   Card purchase at ", "merchant", "Zomato Media Pvt Ltd", "            1280.00              -       141220.00")
    builder.add_planted_field("2026-09-10   Online Utility Bill payment         ", "amount", "3450.00", "              -       137770.00")
    builder.add_planted_field("2026-09-15   Closing Available Balance:                                             ", "balance", "137770.00")
    builder.add_line("================================================================================")
    builder.add_line("END OF STATEMENT - HDFC Bank Limited.")
    return builder.build()


def build_bs3(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("BS-3")
    builder.add_line("================================================================================")
    builder.add_line("                       ICICI BANK - ACCOUNT ACTIVITY STATEMENT                  ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Account Holder:      ", "person_name", "Ananya Deshmukh")
    builder.add_planted_field("Account Number:      ", "account_identifier", "001205004567")
    builder.add_planted_field("Account User ID:     ", "internal_id", "ICICI7749201")
    builder.add_planted_field("Mobile Number:       ", "contact", "+91-9723456789")
    builder.add_planted_field("Residential Address: ", "address", "Flat 14B Palm Grove Bandra West Mumbai 400050")
    builder.add_line("Branch:              Bandra West Mumbai | IFSC: ICIC0000012")
    builder.add_line("Statement Date:      15-Sep-2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Date         Description                        Debit (INR)   Credit (INR)    Balance (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("", "transaction_date", "2026-09-02", "   NEFT Salary Credit                             -       65000.00        95000.00")
    builder.add_planted_field("2026-09-05   E-commerce spend: ", "merchant", "Amazon Retail India", "             3499.00              -        91501.00")
    builder.add_planted_field("2026-09-08   UPI payout to ", "counterparty_name", "Sunil Joshi", "                   1800.00              -        89701.00")
    builder.add_line("             Narration: UPI/sunil.joshi@icici/maintenance")
    builder.add_planted_field("2026-09-11   ATM Cash Withdrawal Bandra           ", "amount", "5000.00", "              -        84701.00")
    builder.add_planted_field("2026-09-15   Net Effective Ledger Balance:                                          ", "balance", "84701.00")
    builder.add_line("================================================================================")
    builder.add_line("END OF STATEMENT - ICICI Bank Ltd.")
    return builder.build()


def build_cc1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("CC-1")
    builder.add_line("================================================================================")
    builder.add_line("                         AXIS BANK - CREDIT CARD STATEMENT                      ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Primary Cardholder:  ", "person_name", "Kavita Nair")
    builder.add_planted_field("Card Number:         ", "account_identifier", "4532-8901-2345-6789")
    builder.add_planted_field("Card Account ID:     ", "internal_id", "AXISCC902341")
    builder.add_planted_field("Contact Phone:       ", "contact", "+91-9849012345")
    builder.add_planted_field("Billing Address:     ", "address", "Plot 56 Jubilee Hills Hyderabad Telangana 500033")
    builder.add_line("Card Type:           Axis Bank Titanium Privilege")
    builder.add_line("Statement Period:    15-Aug-2026 to 14-Sep-2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Date         Transaction Description                           Amount (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("", "transaction_date", "2026-08-20", "   DOMESTIC ONLINE PURCHASE - FLIPKART                   8990.00")
    builder.add_planted_field("             Vendor: ", "merchant", "Flipkart Internet Pvt Ltd")
    builder.add_planted_field("2026-08-28   GROCERY RETAIL STORE HYDERABAD                   ", "amount", "4320.00")
    builder.add_planted_field("2026-09-14   TOTAL STATEMENT OUTSTANDING DUE:                 ", "balance", "32450.00")
    builder.add_line("2026-09-14   Minimum Amount Due:                              3245.00")
    builder.add_line("================================================================================")
    builder.add_line("Payment Due Date: 04-Oct-2026 | Axis Bank Credit Card Division")
    return builder.build()


def build_cc2(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("CC-2")
    builder.add_line("================================================================================")
    builder.add_line("                          SBI CARD - MONTHLY CREDIT STATEMENT                   ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Name of Cardholder:  ", "person_name", "Rajesh Kulkarni")
    builder.add_planted_field("Credit Card Number:  ", "account_identifier", "5241-7600-1122-3344")
    builder.add_planted_field("Reference ID:        ", "internal_id", "SBICUST881923")
    builder.add_planted_field("Mobile Phone:        ", "contact", "+91-9822012345")
    builder.add_planted_field("Billing Residence:   ", "address", "Flat 303 Kothrud Heights Pune Maharashtra 411038")
    builder.add_line("Card Variant:        SBI Card Elite Signature")
    builder.add_line("Billing Cycle:       18-Aug-2026 to 17-Sep-2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Date         Description                                       Amount (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("", "transaction_date", "2026-08-25", "   TRAVEL BOOKING - MAKEMYTRIP                          14500.00")
    builder.add_planted_field("             Merchant Name: ", "merchant", "MakeMyTrip India Pvt Ltd")
    builder.add_planted_field("2026-09-02   ELECTRONICS STORE PUNE                           ", "amount", "7800.00")
    builder.add_planted_field("2026-09-17   CLOSING TOTAL AMOUNT PAYABLE:                    ", "balance", "28900.50")
    builder.add_line("2026-09-17   Payment Due Date: 07-Oct-2026")
    builder.add_line("================================================================================")
    builder.add_line("SBI Cards & Payment Services Ltd.")
    return builder.build()


def build_ps1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("PS-1")
    builder.add_line("================================================================================")
    builder.add_line("                     INFOSYS TECHNOLOGIES - MONTHLY SALARY PAYSLIP              ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Company / Employer:  ", "employer", "Infosys Technologies Ltd")
    builder.add_planted_field("Employee Full Name:  ", "person_name", "Deepak Srinivasan")
    builder.add_planted_field("Employee Code:       ", "internal_id", "EMP104928")
    builder.add_planted_field("Income Tax PAN:      ", "government_id", "ABCPS1234F")
    builder.add_planted_field("Date of Birth:       ", "date_of_birth", "1992-06-15")
    builder.add_planted_field("Phone Contact:       ", "contact", "+91-9840123456")
    builder.add_planted_field("Disbursement Bank Ac:", "account_identifier", "62019482019")
    builder.add_line("Designation:         Lead Systems Engineer | Pay Period: August 2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Earnings Header                         Amount (INR)   Deductions Header               Amount (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("Basic Salary Component:                  ", "salary_component", "55000.00", "   Provident Fund Deduction:        6600.00")
    builder.add_line("House Rent Allowance (HRA):              22000.00   Professional Tax:                 200.00")
    builder.add_line("Special Allowance:                       20000.00   Income Tax Withheld:             2750.00")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Gross Earnings:                          97000.00   Total Deductions:                9550.00")
    builder.add_planted_field("NET TAKE-HOME REMUNERATION:              ", "amount", "87450.00")
    builder.add_line("================================================================================")
    builder.add_line("Corporate Address: Electronics City, Hosur Road, Bengaluru 560100")
    return builder.build()


def build_ps2(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("PS-2")
    builder.add_line("================================================================================")
    builder.add_line("               TATA CONSULTANCY SERVICES - SALARY SLIP (FORM 16 STYLE)          ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Organization Name:   ", "employer", "Tata Consultancy Services Ltd")
    builder.add_planted_field("Staff Member:        ", "person_name", "Meera Sundaram")
    builder.add_planted_field("Staff Identification:", "internal_id", "TCS784910")
    builder.add_planted_field("Permanent Account No:", "government_id", "XYZPM5678K")
    builder.add_planted_field("Birth Date:          ", "date_of_birth", "1988-11-23")
    builder.add_planted_field("Official Contact No: ", "contact", "+91-9820012345")
    builder.add_planted_field("Salary Credit Ac No: ", "account_identifier", "912010045678901")
    builder.add_line("Grade:               Consultant | Location: Mumbai | Pay Cycle: August 2026")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Allowance Description                   Amount (INR)   Statutory Deductions            Amount (INR)")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Basic Pay Structure:                     60000.00   Employee PF Contribution:        7200.00")
    builder.add_planted_field("HRA Salary Component:                    ", "salary_component", "28000.00", "   Tax Deducted at Source (TDS):    4200.00")
    builder.add_line("Performance Incentive:                   20000.00   Statutory Gratuity Provision:     400.00")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("Total Monthly Earnings:                 108000.00   Total Statutory Deductions:     11800.00")
    builder.add_planted_field("DISBURSED NET SALARY AMOUNT:             ", "amount", "96200.00")
    builder.add_line("================================================================================")
    builder.add_line("TCS House, Raveline Street, Fort, Mumbai 400001.")
    return builder.build()


def build_ra1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("RA-1")
    builder.add_line("================================================================================")
    builder.add_line("                          RESIDENTIAL RENT AGREEMENT                            ")
    builder.add_line("================================================================================")
    builder.add_line("This Tenancy Agreement is executed on this 1st day of August 2026 by and between:")
    builder.add_planted_field("LANDLORD (First Party): ", "person_name", "Suresh Chandra Gupta", " son of Late R. K. Gupta")
    builder.add_planted_field("Landlord PAN:           ", "government_id", "ABCPG4321D")
    builder.add_planted_field("Landlord Contact Mobile:", "contact", "+91-9810012345")
    builder.add_line("AND")
    builder.add_planted_field("TENANT (Second Party):  ", "counterparty_name", "Aditya Nambiar", " son of K. V. Nambiar")
    builder.add_planted_field("Leased Property Address:", "address", "House No 24 Defence Colony New Delhi 110024")
    builder.add_planted_field("Registration Docket No: ", "internal_id", "REG-DL-2026-9041")
    builder.add_planted_field("Agreement Start Date:   ", "transaction_date", "2026-08-01")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("TERMS AND CONDITIONS:")
    builder.add_planted_field("1. The Tenant agrees to pay a monthly rent amount of INR ", "amount", "38000.00", " on or before the 5th day of every calendar month.")
    builder.add_planted_field("2. Legal Covenant: ", "clause_text", "The tenant shall pay a refundable security deposit of Rupees 114000 and the lock-in period shall be eleven months.")
    builder.add_line("3. Notice period for vacation of tenancy premises shall be one full calendar month by either party.")
    builder.add_line("================================================================================")
    builder.add_line("IN WITNESS WHEREOF the parties have placed their signatures on the date mentioned above.")
    return builder.build()


def build_ub1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("UB-1")
    builder.add_line("================================================================================")
    builder.add_line("         BANGALORE ELECTRICITY SUPPLY COMPANY LIMITED (BESCOM) - UTILITY BILL   ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Consumer Account ID:    ", "account_identifier", "CA-5409182341")
    builder.add_planted_field("Consumer / Customer Name:", "person_name", "Naveen Ranganathan")
    builder.add_planted_field("Registered Mobile:      ", "contact", "+91-9448012345")
    builder.add_planted_field("Premises Service Address:", "address", "No 88 5th Cross Malleshwaram Bengaluru 560003")
    builder.add_planted_field("Electric Meter Number:  ", "internal_id", "MTR-KA-778201")
    builder.add_line("Sub-Division:           Malleshwaram C-4 | Tariff Category: LT-2(a) Domestic")
    builder.add_line("Billing Period:         01-Aug-2026 to 31-Aug-2026 | Meter Constant: 1.0")
    builder.add_line("Previous Reading: 4120 units | Current Reading: 4540 units | Billed Consumption: 420 kWh")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("Total Current Bill Payable Amount:        INR ", "amount", "4180.00")
    builder.add_planted_field("Due Date for Payment:                         ", "transaction_date", "2026-09-25")
    builder.add_planted_field("Regulatory Clause: ", "clause_text", "Failure to pay before the due date will attract a surcharge of 2 percent per month and immediate disconnection without further notice.")
    builder.add_line("================================================================================")
    builder.add_line("For grievances call BESCOM 24x7 Helpline: 1912 | Save Electricity for a Greener Tomorrow")
    return builder.build()


def build_il1(rng: random.Random) -> Tuple[str, List[PlantedItem]]:
    builder = DocumentBuilder("IL-1")
    builder.add_line("================================================================================")
    builder.add_line("           APOLLO CLINICAL DIAGNOSTICS & HEALTH INSURANCE SUMMARY REPORT        ")
    builder.add_line("================================================================================")
    builder.add_planted_field("Health Policy / Member ID:   ", "internal_id", "POL-STAR-8849201")
    builder.add_planted_field("Patient Full Name:           ", "person_name", "Harish Venkataraman")
    builder.add_planted_field("Patient Date of Birth:       ", "date_of_birth", "1975-04-10")
    builder.add_planted_field("Emergency Contact Mobile:    ", "contact", "+91-9841012345")
    builder.add_planted_field("National Health / ABHA ID:   ", "government_id", "ABHA-91-8823-4410")
    builder.add_line("Doctor in Charge:            Dr. S. K. Ramanathan, MD (Internal Medicine)")
    builder.add_line("Specimen Collection Date:    05-Sep-2026 | Fasting Specimen: YES")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_line("CLINICAL LABORATORY FINDINGS:")
    builder.add_planted_field("Biochemical Profile:         ", "medical_value", "HbA1c: 8.4 percent, Fasting Blood Sugar: 168 mg/dL")
    builder.add_line("Reference Normal Ranges:     HbA1c < 5.7 percent, Fasting Glucose 70-99 mg/dL")
    builder.add_line("Diagnostic Clinical Remarks: Uncontrolled Type 2 Diabetes Mellitus with hyperglycemia")
    builder.add_line("--------------------------------------------------------------------------------")
    builder.add_planted_field("Total Incurred Investigation Bill:       INR ", "amount", "6500.00")
    builder.add_planted_field("Policy Insurance Coverage Condition:     ", "clause_text", "Pre-existing conditions for diabetes mellitus are subject to a 24-month waiting period from policy inception date.")
    builder.add_line("================================================================================")
    builder.add_line("Apollo Diagnostics Ltd. | Valid for cashless claim adjudication under TPA guidelines.")
    return builder.build()


def generate_corpus(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    """Generates all 10 documents and writes them to corpus/ along with planted.json."""
    rng = random.Random(seed)
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    doc_generators = [
        ("BS-1", build_bs1),
        ("BS-2", build_bs2),
        ("BS-3", build_bs3),
        ("CC-1", build_cc1),
        ("CC-2", build_cc2),
        ("PS-1", build_ps1),
        ("PS-2", build_ps2),
        ("RA-1", build_ra1),
        ("UB-1", build_ub1),
        ("IL-1", build_il1),
    ]

    all_planted: List[Dict[str, Any]] = []
    inventory: Dict[str, Dict[str, Any]] = {}

    for doc_id, gen_fn in doc_generators:
        content, planted = gen_fn(rng)
        doc_file = CORPUS_DIR / f"{doc_id}.txt"
        with open(doc_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Count by category for reporting
        category_counts: Dict[str, int] = {}
        for item in planted:
            all_planted.append(asdict(item))
            category_counts[item.category] = category_counts.get(item.category, 0) + 1

        inventory[doc_id] = {
            "file": doc_file.name,
            "char_count": len(content),
            "line_count": len(content.splitlines()),
            "planted_count": len(planted),
            "categories": category_counts,
        }

    with open(PLANTED_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(all_planted, f, indent=2)

    return {
        "seed": seed,
        "document_count": len(doc_generators),
        "total_planted_items": len(all_planted),
        "documents": inventory,
    }


if __name__ == "__main__":
    summary = generate_corpus()
    print(f"Generated {summary['document_count']} documents with {summary['total_planted_items']} planted items.")
