from datetime import datetime

from pydantic import BaseModel

from app.dto.entity.base_entity import BaseEntity



class Balance (BaseEntity, BaseModel):
    bankName: str | None = None # Bank or fiduciary name MANDATORY
    bankNit: str | None = None # Bank or fiduciary NIT MANDATORY for FBogota
    accountHolder: str | None = None # Account holder MANDATORY for fbogota
    currency: str | None = None # Is always filled by default, but can be overriden MANDATORY
    balanceDate: datetime | None = None # Date of the balance MANDATORY, if not filled, it will be extracted from the filename
    totalOrders: float | None = None # Total encargos balance, MANDATORY IN FBogota and imperative to validate
    totalOrdersExchange: float | None = None # Total encargos balance in canje currency, MANDATORY IN FBogota and imperative to validate
    totalOrdersAvailable: float | None = None # Total encargos available balance, MANDATORY IN FBogota and imperative to validate
    totalAccounts: float | None = None # Total accounts balance, MANDATORY IN FBogota and imperative to validate
    totalAccountsExchange: float | None = None # Total accounts balance in exchange currency, MANDATORY IN FBogota and imperative to validate
    totalAccountsAvailable: float | None = None # Total accounts available balance, MANDATORY IN FBogota and imperative to validate
    details: list['BalanceDetail'] = [] # List of balance details, MANDATORY for all formats



class BalanceDetail(BaseModel):
    accountNumber: str | None = None # Account number MANDATORY can be ofuscated
    accountType: str | None = None # Account type MANDATORY encargo|cuenta, the model determines the type
    totalBalance: float | None = None # Total balance MANDATORY
    exchangeBalance: float | None = None # Total balance in canje MANDATORY for FBogota
    availableBalance: float | None = None # Available balance MANDATORY but in Alianza is total_balance
    participation: str | None = None # Participation in the encargo, MANDATORY for FDavivienda
    fund: str | None = None # Fund name, MANDATORY for FDavivienda and FBogota is called Tipo de Cuenta in FAlianza
    date: datetime | None = None # Date of the account, filled with the balance date if not provided
    
