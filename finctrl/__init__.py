from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    ForeignKeyField,
    DateField,
    DecimalField,
    DateTimeField,
    IntegerField,
    TextField
)

import os
import click
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from enum import IntEnum
from calendar import monthrange

db = SqliteDatabase(os.path.join(os.getcwd(), 'finance.db'))


class Currency(Model):
    name = CharField()
    code = CharField()
    sign = CharField()

    class Meta:
        database = db


class Account(Model):
    name = CharField()
    currency = ForeignKeyField(Currency, related_name='accounts')

    class Meta:
        database = db


class AccountBalance(Model):
    account = ForeignKeyField(Account, related_name='balance_entries')
    date = DateField()
    balance = DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        database = db


class TransactionType(IntEnum):
    DEBIT = 1
    CREDIT = 2
    TRANSFER_OUT = 3
    TRANSFER_IN = 4


class AccountTransaction(Model):
    account = ForeignKeyField(Account, related_name='transactions')
    timestamp = DateTimeField()
    type = IntegerField()
    amount = DecimalField(max_digits=10, decimal_places=2)
    comment = TextField()

    class Meta:
        database = db


def init_db():
    db.create_tables([Currency, Account, AccountBalance, AccountTransaction], safe=True)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('name')
@click.argument('code')
@click.argument('sign')
def create_currency(name, code, sign):
    init_db()
    currency = Currency.create(
        name=name,
        code=code,
        sign=sign
    )
    currency.save()
    click.echo('Created Currency instance #{0}'.format(currency.id))


@cli.command()
@click.argument('currency_id', type=click.INT)
@click.argument('sign')
def edit_currency_sign(currency_id, sign):
    init_db()
    currency = Currency.get(Currency.id == currency_id)
    currency.sign = sign
    currency.save()


@cli.command()
def list_currencies():
    init_db()
    currencies = Currency.select()
    for currency in currencies:
        click.echo('#{0} "{1}" {2} {3}'.format(currency.id, currency.name, currency.code, currency.sign))


@cli.command()
@click.argument('name')
@click.argument('currency_code')
def create_account(name, currency_code):
    init_db()
    currency = Currency.get(Currency.code == currency_code)
    account = Account.create(
        name=name,
        currency=currency
    )
    account.save()
    click.echo('Created Account instance #{0}'.format(account.id))


@cli.command()
@click.argument('account_id', type=click.INT)
@click.argument('name')
def rename_account(account_id, name):
    init_db()
    account = Account.get(Account.id == account_id)
    account.name = name
    account.save()


@cli.command()
def list_accounts():
    init_db()
    accounts = Account.select()
    for account in accounts:
        click.echo('#{0} "{1}" {2}'.format(account.id, account.name, account.currency.code))


@cli.command()
@click.argument('account_id', type=click.INT)
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
@click.argument('balance')
def create_account_balance_entry(account_id, year, month, day, balance):
    init_db()
    account = Account.get(Account.id == account_id)
    balance_date = date(year, month, day)
    balance_decimal = Decimal(balance)
    balance_entry = AccountBalance(
        account=account,
        date=balance_date,
        balance=balance_decimal
    )
    balance_entry.save()


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
def list_account_balance_entries(year, month, day):
    init_db()
    balance_date = date(year, month, day)
    account_balance_entries = AccountBalance.select().where(AccountBalance.date == balance_date)
    for entry in account_balance_entries:
        click.echo('#{0} "{1}" {2} {3} {4}'.format(entry.id, entry.account.name, entry.date, entry.balance, entry.account.currency.sign))


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
def update_account_balance_entries(year, month, day):
    init_db()
    date_cur = date(year, month, day)
    date_day_before = date_cur - timedelta(days=1)
    for account in Account.select():
        try:
            balance_cur = AccountBalance.select().where(AccountBalance.account == account).where(AccountBalance.date == date_cur).get()
            click.echo('#{0} "{1}" {2} {3} {4}'.format(balance_cur.id, balance_cur.account.name, balance_cur.date, balance_cur.balance, balance_cur.account.currency.sign))
        except AccountBalance.DoesNotExist:
            try:
                balance_day_before = AccountBalance.select().where(AccountBalance.account == account).where(AccountBalance.date == date_day_before).get()
                transactions = AccountTransaction.select().where(
                    AccountTransaction.account == account
                ).where(
                    AccountTransaction.timestamp.year == date_day_before.year
                ).where(
                    AccountTransaction.timestamp.month == date_day_before.month
                ).where(
                    AccountTransaction.timestamp.day == date_day_before.day
                )
                balance = balance_day_before.balance
                for transaction in transactions:
                    if transaction.type in (TransactionType.DEBIT, TransactionType.TRANSFER_OUT):
                        balance = (balance - transaction.amount).quantize(Decimal('.01'))
                    elif transaction.type in (TransactionType.CREDIT, TransactionType.TRANSFER_IN):
                        balance = (balance + transaction.amount).quantize(Decimal('.01'))
                balance_entry = AccountBalance(
                    account=account,
                    date=date_cur,
                    balance=balance
                )
                balance_entry.save()
            except AccountBalance.DoesNotExist:
                print('Not OK')


@cli.command()
@click.argument('account_id', type=click.INT)
@click.argument('type', type=click.Choice([TransactionType.DEBIT.name, TransactionType.CREDIT.name, TransactionType.TRANSFER_OUT.name, TransactionType.TRANSFER_IN.name]))
@click.argument('amount')
@click.argument('comment')
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
@click.argument('hour', type=click.INT, default=datetime.now().hour)
@click.argument('minute', type=click.INT, default=datetime.now().minute)
@click.argument('second', type=click.INT, default=datetime.now().second)
def create_account_transaction(account_id, type, amount, comment, year, month, day, hour, minute, second):
    init_db()
    account = Account.get(Account.id == account_id)
    timestamp = datetime(year, month, day, hour, minute, second)
    amount_decimal = Decimal(amount)
    object_type = TransactionType[type]
    transaction = AccountTransaction(
        account=account,
        timestamp=timestamp,
        type=object_type.value,
        amount=amount_decimal,
        comment=comment
    )
    transaction.save()


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
def list_account_transactions(year, month, day):
    init_db()
    balance_date = date(year, month, day)
    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp.year == balance_date.year
    ).where(
        AccountTransaction.timestamp.month == balance_date.month
    ).where(
        AccountTransaction.timestamp.day == balance_date.day
    )
    for entry in account_transactions:
        click.echo('#{0} "{1}" {2} {3} {4} {5} "{6}"'.format(entry.id, entry.account.name, entry.timestamp, TransactionType(entry.type).name, entry.amount, entry.account.currency.sign, entry.comment))


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
def list_account_transactions_month(year, month):
    init_db()
    balance_date = date(year, month, 1)
    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp.year == balance_date.year
    ).where(
        AccountTransaction.timestamp.month == balance_date.month
    )
    for entry in account_transactions:
        click.echo('#{0} "{1}" {2} {3} {4} {5} "{6}"'.format(entry.id, entry.account.name, entry.timestamp, TransactionType(entry.type).name, entry.amount, entry.account.currency.sign, entry.comment))


@cli.command()
@click.argument('transaction_id', click.INT)
def remove_account_transaction(transaction_id):
    init_db()
    transaction = AccountTransaction.get(AccountTransaction.id == transaction_id)
    transaction.delete_instance()


@cli.command()
@click.argument('account_id', click.INT)
def remove_account(account_id):
    init_db()
    account = Account.get(Account.id == account_id)
    account.delete_instance()


@cli.command()
@click.argument('entry_id', click.INT)
def remove_account_balance_entry(entry_id):
    init_db()
    transaction = AccountBalance.get(AccountBalance.id == entry_id)
    transaction.delete_instance()


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
def show_monthly_report(year, month):
    init_db()
    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp.year == year
    ).where(
        AccountTransaction.timestamp.month == month
    )

    monthly_credit = {}
    monthly_debit = {}

    for entry in account_transactions:
        if entry.type == TransactionType.DEBIT:
            if entry.account.currency not in monthly_debit:
                monthly_debit[entry.account.currency] = Decimal('0.00')
            monthly_debit[entry.account.currency] += entry.amount
        elif entry.type == TransactionType.CREDIT:
            if entry.account.currency not in monthly_credit:
                monthly_credit[entry.account.currency] = Decimal('0.00')
            monthly_credit[entry.account.currency] += entry.amount

    for currency, amount in monthly_credit.items():
        click.echo('CREDIT: {0} {1}'.format(amount, currency.sign))

    for currency, amount in monthly_debit.items():
        click.echo('DEBIT: {0} {1}'.format(amount, currency.sign))


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
def show_balance_report(year, month, day):
    init_db()
    balance_date = date(year, month, day)
    account_balance_entries = AccountBalance.select().where(AccountBalance.date == balance_date)
    balance_map = {}
    for entry in account_balance_entries:
        if entry.account.currency not in balance_map:
            balance_map[entry.account.currency] = Decimal('0.00')
        balance_map[entry.account.currency] += entry.balance

    for currency, balance in balance_map.items():
        click.echo('{0} - {1} {2}'.format(currency.code, balance, currency.sign))


@cli.command()
@click.argument('start_year', type=click.INT)
@click.argument('start_month', type=click.INT)
@click.argument('end_year', type=click.INT)
@click.argument('end_month', type=click.INT)
@click.argument('exclude_accounts', default='0')
@click.argument('exclude_transactions', default='0')
def show_average_overview(start_year, start_month, end_year, end_month,
                          exclude_accounts, exclude_transactions):
    init_db()

    start_day = 1
    start_date = date(start_year, start_month, start_day)
    _, end_day = monthrange(end_year, end_month)
    end_date = date(end_year, end_month, end_day)
    # click.echo(start_date)
    # click.echo(end_date)

    num_months = 0
    ndx_date = start_date
    while True:
        num_months += 1
        if ndx_date.year == end_year and ndx_date.month == end_month:
            break
        _, num_days = monthrange(ndx_date.year, ndx_date.month)
        ndx_date = ndx_date + timedelta(days=num_days)
    # click.echo(num_months)
    exclude_accounts = [int(x) for x in exclude_accounts.split(',')]
    # click.echo(exclude_accounts)
    exclude_transactions = [int(x) for x in exclude_transactions.split(',')]

    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp >= start_date
    ).where(
        AccountTransaction.timestamp <= end_date
    ).where(
        AccountTransaction.account_id.not_in(exclude_accounts)
    ).where(
        AccountTransaction.id.not_in(exclude_transactions)
    )

    total_credit = {}
    total_debit = {}

    for entry in account_transactions:
        if entry.type == TransactionType.DEBIT:
            if entry.account.currency not in total_debit:
                total_debit[entry.account.currency] = Decimal('0.00')
            total_debit[entry.account.currency] += entry.amount
            click.echo('#{0} "{1}" {2} {3} {4} {5} "{6}"'.format(entry.id, entry.account.name, entry.timestamp, TransactionType(entry.type).name, entry.amount, entry.account.currency.sign, entry.comment))
        elif entry.type == TransactionType.CREDIT:
            if entry.account.currency not in total_credit:
                total_credit[entry.account.currency] = Decimal('0.00')
            total_credit[entry.account.currency] += entry.amount
            click.echo('#{0} "{1}" {2} {3} {4} {5} "{6}"'.format(entry.id, entry.account.name, entry.timestamp, TransactionType(entry.type).name, entry.amount, entry.account.currency.sign, entry.comment))

    for currency, amount in total_credit.items():
        click.echo('CREDIT: {0} {1}'.format(amount, currency.sign))
        click.echo('CREDIT AVG: {0} {1}'.format(Decimal(amount / num_months).quantize(Decimal('.01'), rounding=ROUND_DOWN), currency.sign))

    for currency, amount in total_debit.items():
        click.echo('DEBIT: {0} {1}'.format(amount, currency.sign))
        click.echo('DEBIT AVG: {0} {1}'.format(Decimal(amount / num_months).quantize(Decimal('.01'), rounding=ROUND_DOWN), currency.sign))


@cli.command()
@click.argument('account_id', click.INT)
@click.argument('start_year', type=click.INT, default=date.today().year)
@click.argument('start_month', type=click.INT, default=date.today().month)
@click.argument('start_day', type=click.INT, default=date.today().day)
def remove_account_balance_entry_series(account_id, start_year, start_month, start_day):
    init_db()
    balance_date = date(start_year, start_month, start_day)
    account_balance_entries = AccountBalance.select().where(
        AccountBalance.account_id == account_id
    ).where(
        AccountBalance.date >= balance_date
    )
    for entry in account_balance_entries:
        entry.delete_instance()


@cli.command()
@click.argument('year', type=click.INT, default=date.today().year)
@click.argument('month', type=click.INT, default=date.today().month)
@click.argument('day', type=click.INT, default=date.today().day)
def update_account_balance_entry_series(year, month, day):
    init_db()
    date_today = date.today()
    date_cur = date(year, month, day)
    while date_cur <= date_today:
        date_day_before = date_cur - timedelta(days=1)
        for account in Account.select():
            try:
                balance_cur = AccountBalance.select().where(AccountBalance.account == account).where(AccountBalance.date == date_cur).get()
                click.echo('#{0} "{1}" {2} {3} {4}'.format(balance_cur.id, balance_cur.account.name, balance_cur.date, balance_cur.balance, balance_cur.account.currency.sign))
            except AccountBalance.DoesNotExist:
                try:
                    balance_day_before = AccountBalance.select().where(AccountBalance.account == account).where(AccountBalance.date == date_day_before).get()
                    transactions = AccountTransaction.select().where(
                        AccountTransaction.account == account
                    ).where(
                        AccountTransaction.timestamp.year == date_day_before.year
                    ).where(
                        AccountTransaction.timestamp.month == date_day_before.month
                    ).where(
                        AccountTransaction.timestamp.day == date_day_before.day
                    )
                    balance = balance_day_before.balance
                    for transaction in transactions:
                        if transaction.type in (TransactionType.DEBIT, TransactionType.TRANSFER_OUT):
                            balance = (balance - transaction.amount).quantize(Decimal('.01'))
                        elif transaction.type in (TransactionType.CREDIT, TransactionType.TRANSFER_IN):
                            balance = (balance + transaction.amount).quantize(Decimal('.01'))
                    balance_entry = AccountBalance(
                        account=account,
                        date=date_cur,
                        balance=balance
                    )
                    balance_entry.save()
                except AccountBalance.DoesNotExist:
                    print('Not OK')
        date_cur = date_cur + timedelta(days=1)


@cli.command()
@click.argument('account_id', click.INT)
@click.argument('start_year', type=click.INT)
@click.argument('start_month', type=click.INT)
@click.argument('start_day', type=click.INT)
@click.argument('end_year', type=click.INT)
@click.argument('end_month', type=click.INT)
@click.argument('end_day', type=click.INT)
def make_account_report(account_id, start_year, start_month, start_day, end_year, end_month, end_day):
    init_db()
    date_start = date(start_year, start_month, start_day)
    date_end = date(end_year, end_month, end_day)

    start_balance_query = AccountBalance.select().where(
        AccountBalance.account_id == account_id,
        AccountBalance.date == date_start
    )

    if start_balance_query.count() == 1:
        start_balance = start_balance_query.get().balance
    else:
        start_balance = Decimal('0.00')

    end_balance_query = AccountBalance.select().where(
        AccountBalance.account_id == account_id,
        AccountBalance.date == date_end
    )

    if end_balance_query.count() == 1:
        end_balance = end_balance_query.get().balance
    else:
        end_balance = Decimal('0.00')

    balance = start_balance

    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp >= date_start
    ).where(
        AccountTransaction.timestamp < date_end
    ).where(
        AccountTransaction.account_id == account_id
    )

    credit = Decimal('0.00')
    debit = Decimal('0.00')

    for entry in account_transactions:
        if entry.type == TransactionType.DEBIT or entry.type == TransactionType.TRANSFER_OUT:
            debit += entry.amount
        if entry.type == TransactionType.CREDIT or entry.type == TransactionType.TRANSFER_IN:
            credit += entry.amount

    print(date_start, start_balance)
    print('credit', credit)
    print('debit', debit)
    print(date_end, end_balance)


@cli.command()
@click.argument('account_id', click.INT)
@click.argument('start_year', type=click.INT)
@click.argument('start_month', type=click.INT)
@click.argument('start_day', type=click.INT)
@click.argument('end_year', type=click.INT)
@click.argument('end_month', type=click.INT)
@click.argument('end_day', type=click.INT)
def list_account_transactions_series(account_id, start_year, start_month, start_day, end_year, end_month, end_day):
    init_db()
    date_start = date(start_year, start_month, start_day)
    date_end = date(end_year, end_month, end_day)

    account_transactions = AccountTransaction.select().where(
        AccountTransaction.timestamp >= date_start
    ).where(
        AccountTransaction.timestamp < date_end
    ).where(
        AccountTransaction.account_id == account_id
    )

    for entry in account_transactions:
        click.echo('#{0} "{1}" {2} {3} {4} {5} "{6}"'.format(entry.id, entry.account.name, entry.timestamp, TransactionType(entry.type).name, entry.amount, entry.account.currency.sign, entry.comment))


if __name__ == '__main__':
    cli()
