"""
Phase 3: Extraction Schemas
============================
Pydantic models for structured document extraction.
Based on L5 notebook schema definitions.

Author: ICR Integration Team
Date: 2026-01-23
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum


class InvoiceSchema(BaseModel):
    """Schema for invoice document extraction."""
    
    invoice_number: str = Field(
        description="Unique invoice identifier or number"
    )
    invoice_date: str = Field(
        description="Date the invoice was issued (YYYY-MM-DD)"
    )
    due_date: Optional[str] = Field(
        None,
        description="Payment due date (YYYY-MM-DD)"
    )
    
    # Vendor information
    vendor_name: str = Field(
        description="Name of the vendor/supplier"
    )
    vendor_address: Optional[str] = Field(
        None,
        description="Vendor's address"
    )
    vendor_tax_id: Optional[str] = Field(
        None,
        description="Vendor's tax ID or registration number"
    )
    
    # Customer information
    customer_name: Optional[str] = Field(
        None,
        description="Name of the customer/buyer"
    )
    customer_address: Optional[str] = Field(
        None,
        description="Customer's billing address"
    )
    
    # Financial details
    subtotal: float = Field(
        description="Subtotal amount before tax"
    )
    tax_amount: Optional[float] = Field(
        None,
        description="Total tax amount"
    )
    total_amount: float = Field(
        description="Total amount due including tax"
    )
    currency: Optional[str] = Field(
        "USD",
        description="Currency code (e.g., USD, EUR)"
    )
    
    # Line items
    line_items: Optional[List[dict]] = Field(
        None,
        description="List of line items with description, quantity, price"
    )
    
    # Payment terms
    payment_terms: Optional[str] = Field(
        None,
        description="Payment terms (e.g., Net 30)"
    )


class W2Schema(BaseModel):
    """Schema for W-2 tax form extraction."""
    
    # Employee information
    employee_name: str = Field(
        description="Full name of the employee"
    )
    employee_ssn: str = Field(
        description="Employee's Social Security Number (last 4 digits preferred)"
    )
    employee_address: str = Field(
        description="Employee's home address"
    )
    
    # Employer information
    employer_name: str = Field(
        description="Name of the employer"
    )
    employer_ein: str = Field(
        description="Employer's Federal Identification Number (EIN)"
    )
    employer_address: str = Field(
        description="Employer's address"
    )
    
    # Tax year
    w2_year: int = Field(
        description="Tax year for this W-2 form"
    )
    
    # Wage and tax information
    wages_box_1: float = Field(
        description="Box 1: Wages, tips, other compensation"
    )
    federal_tax_withheld_box_2: float = Field(
        description="Box 2: Federal income tax withheld"
    )
    social_security_wages_box_3: Optional[float] = Field(
        None,
        description="Box 3: Social security wages"
    )
    social_security_tax_box_4: Optional[float] = Field(
        None,
        description="Box 4: Social security tax withheld"
    )
    medicare_wages_box_5: Optional[float] = Field(
        None,
        description="Box 5: Medicare wages and tips"
    )
    medicare_tax_box_6: Optional[float] = Field(
        None,
        description="Box 6: Medicare tax withheld"
    )
    
    # State information (if applicable)
    state: Optional[str] = Field(
        None,
        description="State abbreviation"
    )
    state_wages: Optional[float] = Field(
        None,
        description="State wages, tips, etc."
    )
    state_tax: Optional[float] = Field(
        None,
        description="State income tax withheld"
    )


class PayStubSchema(BaseModel):
    """Schema for pay stub extraction."""
    
    # Employee information
    employee_name: str = Field(
        description="Employee's full name"
    )
    employee_id: Optional[str] = Field(
        None,
        description="Employee ID or number"
    )
    
    # Employer information
    employer_name: str = Field(
        description="Employer's name"
    )
    
    # Pay period
    pay_period_start: str = Field(
        description="Pay period start date (YYYY-MM-DD)"
    )
    pay_period_end: str = Field(
        description="Pay period end date (YYYY-MM-DD)"
    )
    pay_date: str = Field(
        description="Payment date (YYYY-MM-DD)"
    )
    
    # Earnings
    gross_pay: float = Field(
        description="Gross pay for the period"
    )
    net_pay: float = Field(
        description="Net pay after deductions"
    )
    
    # Year-to-date totals
    ytd_gross: Optional[float] = Field(
        None,
        description="Year-to-date gross earnings"
    )
    ytd_net: Optional[float] = Field(
        None,
        description="Year-to-date net pay"
    )
    
    # Deductions
    federal_tax: Optional[float] = Field(
        None,
        description="Federal income tax withheld"
    )
    state_tax: Optional[float] = Field(
        None,
        description="State income tax withheld"
    )
    social_security: Optional[float] = Field(
        None,
        description="Social security tax"
    )
    medicare: Optional[float] = Field(
        None,
        description="Medicare tax"
    )


class BankStatementSchema(BaseModel):
    """Schema for bank statement extraction."""
    
    # Account information
    account_holder_name: str = Field(
        description="Name of the account holder"
    )
    account_number: str = Field(
        description="Account number (last 4 digits preferred)"
    )
    account_type: Optional[str] = Field(
        None,
        description="Type of account (checking, savings, etc.)"
    )
    
    # Bank information
    bank_name: str = Field(
        description="Name of the financial institution"
    )
    
    # Statement period
    statement_period_start: str = Field(
        description="Statement period start date (YYYY-MM-DD)"
    )
    statement_period_end: str = Field(
        description="Statement period end date (YYYY-MM-DD)"
    )
    
    # Balances
    beginning_balance: float = Field(
        description="Balance at start of statement period"
    )
    ending_balance: float = Field(
        description="Balance at end of statement period"
    )
    
    # Summary
    total_deposits: Optional[float] = Field(
        None,
        description="Total deposits during period"
    )
    total_withdrawals: Optional[float] = Field(
        None,
        description="Total withdrawals during period"
    )
    
    # Transactions (optional - may be too many)
    num_transactions: Optional[int] = Field(
        None,
        description="Number of transactions in statement"
    )


class DriverLicenseSchema(BaseModel):
    """Schema for driver's license extraction."""
    
    # Personal information
    full_name: str = Field(
        description="Full legal name"
    )
    date_of_birth: str = Field(
        description="Date of birth (YYYY-MM-DD)"
    )
    gender: Optional[str] = Field(
        None,
        description="Gender (M/F/X)"
    )
    
    # Physical characteristics
    height: Optional[str] = Field(
        None,
        description="Height (e.g., 5'10\")"
    )
    weight: Optional[str] = Field(
        None,
        description="Weight in pounds"
    )
    eye_color: Optional[str] = Field(
        None,
        description="Eye color"
    )
    
    # License information
    license_number: str = Field(
        description="Driver's license number"
    )
    license_class: Optional[str] = Field(
        None,
        description="License class/type"
    )
    issue_date: str = Field(
        description="Date license was issued (YYYY-MM-DD)"
    )
    expiration_date: str = Field(
        description="Expiration date (YYYY-MM-DD)"
    )
    
    # Address
    address: str = Field(
        description="Residential address"
    )
    city: str = Field(
        description="City"
    )
    state: str = Field(
        description="State abbreviation"
    )
    zip_code: str = Field(
        description="ZIP code"
    )


class PassportSchema(BaseModel):
    """Schema for passport extraction."""
    
    # Personal information
    surname: str = Field(
        description="Last name / surname"
    )
    given_names: str = Field(
        description="Given names / first and middle names"
    )
    nationality: str = Field(
        description="Nationality/citizenship"
    )
    date_of_birth: str = Field(
        description="Date of birth (YYYY-MM-DD)"
    )
    place_of_birth: Optional[str] = Field(
        None,
        description="Place/country of birth"
    )
    gender: str = Field(
        description="Gender (M/F/X)"
    )
    
    # Passport information
    passport_number: str = Field(
        description="Passport number"
    )
    passport_type: Optional[str] = Field(
        None,
        description="Type of passport (e.g., P for personal)"
    )
    country_code: str = Field(
        description="Issuing country code (3-letter)"
    )
    
    # Dates
    issue_date: str = Field(
        description="Date of issue (YYYY-MM-DD)"
    )
    expiration_date: str = Field(
        description="Expiration date (YYYY-MM-DD)"
    )
    
    # Additional
    authority: Optional[str] = Field(
        None,
        description="Issuing authority"
    )


class ContractSchema(BaseModel):
    """Schema for contract document extraction."""
    
    # Contract details
    contract_title: str = Field(
        description="Title or type of contract"
    )
    contract_date: str = Field(
        description="Date contract was signed (YYYY-MM-DD)"
    )
    effective_date: Optional[str] = Field(
        None,
        description="Date contract becomes effective (YYYY-MM-DD)"
    )
    expiration_date: Optional[str] = Field(
        None,
        description="Contract expiration date (YYYY-MM-DD)"
    )
    
    # Parties
    party_a_name: str = Field(
        description="Name of first party"
    )
    party_b_name: str = Field(
        description="Name of second party"
    )
    
    # Financial terms
    contract_value: Optional[float] = Field(
        None,
        description="Total contract value"
    )
    payment_terms: Optional[str] = Field(
        None,
        description="Payment terms and schedule"
    )
    
    # Key terms
    scope_of_work: Optional[str] = Field(
        None,
        description="Brief description of scope of work"
    )
    termination_clause: Optional[str] = Field(
        None,
        description="Termination conditions"
    )


class ReceiptSchema(BaseModel):
    """Schema for receipt extraction."""
    
    # Merchant information
    merchant_name: str = Field(
        description="Name of the merchant/store"
    )
    merchant_address: Optional[str] = Field(
        None,
        description="Merchant's address"
    )
    
    # Receipt details
    receipt_number: Optional[str] = Field(
        None,
        description="Receipt or transaction number"
    )
    transaction_date: str = Field(
        description="Date of transaction (YYYY-MM-DD)"
    )
    transaction_time: Optional[str] = Field(
        None,
        description="Time of transaction (HH:MM)"
    )
    
    # Financial details
    subtotal: float = Field(
        description="Subtotal before tax"
    )
    tax: Optional[float] = Field(
        None,
        description="Tax amount"
    )
    total: float = Field(
        description="Total amount paid"
    )
    
    # Payment method
    payment_method: Optional[str] = Field(
        None,
        description="Payment method used (cash, credit, etc.)"
    )
    
    # Items
    items: Optional[List[dict]] = Field(
        None,
        description="List of purchased items"
    )


# Schema registry for document type mapping
SCHEMA_REGISTRY = {
    'invoice': InvoiceSchema,
    'W2': W2Schema,
    'pay_stub': PayStubSchema,
    'bank_statement': BankStatementSchema,
    'driver_license': DriverLicenseSchema,
    'passport': PassportSchema,
    'contract': ContractSchema,
    'receipt': ReceiptSchema
}


def get_schema_for_document_type(doc_type: str) -> Optional[BaseModel]:
    """
    Get Pydantic schema for a document type.
    
    Args:
        doc_type: Document type string
        
    Returns:
        Pydantic model class or None if not found
    """
    return SCHEMA_REGISTRY.get(doc_type.lower())


def get_all_schemas() -> Dict[str, BaseModel]:
    """Get all available schemas."""
    return SCHEMA_REGISTRY.copy()


def get_schema_fields(schema: BaseModel) -> List[str]:
    """
    Get list of field names from a schema.
    
    Args:
        schema: Pydantic model class
        
    Returns:
        List of field names
    """
    if hasattr(schema, '__annotations__'):
        return list(schema.__annotations__.keys())
    return []
