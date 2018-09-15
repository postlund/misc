#!/usr/bin/env python3
"""Script to download and present receipts from City Gross."""

import sys
import asyncio
import argparse
from collections import namedtuple

import aiohttp
import tabulate


LOGIN_URL = 'https://publicapi.citygross.se/publickdb/odata/Logins/SignIn'
RECEIPTS_URL = 'https://publicapi.citygross.se/PublicContent/api/receipts'


Article = namedtuple('Article', 'name purchases')
Purchase = namedtuple('Purchase', 'unit_price total_price')


async def login(session, email, password):
    """Login and return authorization token."""
    req = {
        'Email': email,
        'Password': password
        }
    headers = {'Content-Type': 'application/json'}

    async with session.post(LOGIN_URL, headers=headers, json=req) as resp:
        resp = await resp.json()
        return resp['Uid']


async def get_receipts(session, token):
    """Get receipts and convert to local representation."""
    req = {
        "QueryParams": [
            "$orderBy=endDateTimeUtc desc",
            "$filter=flags/isDeleted eq false"
            ]
        }
    headers = {'Content-Type': 'application/json',
               'Authorization': 'Bearer ' + token}

    async with session.post(RECEIPTS_URL, headers=headers, json=req) as resp:
        json_response = await resp.json()
        return parse_receipts(json_response)


def parse_receipts(data):
    """Parse server json response to local representation."""
    all_items = {}

    for receipt in data:
        for item in receipt['items']:
            article_number = item['article']['itemNumber']
            article_text = item['article']['itemText']

            if article_number not in all_items:
                all_items[article_number] = Article(article_text, [])

            all_items[article_number].purchases.append(
                Purchase(item['unitPrice'], item['total']))

    return all_items


def list_of_purchases(receipts):
    """Return list of purchase information from receipts."""
    for article in sorted(receipts):
        purchase_count = len(article.purchases)
        total_price = sum([x.total_price for x in article.purchases])
        unit_prices = ', '.join([str(x.unit_price) for x in article.purchases])
        yield purchase_count, article.name, total_price, unit_prices


async def print_receipts(email, password):
    """Download receipts and print a summary."""
    async with aiohttp.ClientSession() as session:
        token = await login(session, email, password)
        receipts = await get_receipts(session, token)

        print(tabulate.tabulate(
            list_of_purchases(receipts.values()),
            headers=['Count', 'Item', 'Total Price', 'Unit Prices']))


async def main():
    """Script starts here."""
    parser = argparse.ArgumentParser(
        description='fetch receipt data from City Gross')
    parser.add_argument('command', help='what to do')
    parser.add_argument('-e', '--email', help='email address')
    parser.add_argument('-p', '--password', help='account password')

    args = parser.parse_args()
    if not args.email or not args.password:
        parser.error('Email and password must be specified')

    # Only one command supported for now
    if args.command == 'print':
        await print_receipts(args.email, args.password)
    else:
        print('Unknown command:', args.command, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
