# -*- coding: utf-8 -*-
import unittest
import time
from datetime import datetime, timedelta

from openprocurement_client.resources.assets import AssetsClient
from openprocurement_client.resources.lots import LotsClient
from openprocurement_client.clients import APIResourceClient

from openregistry.api.tests.blanks.json_data import (
    test_organization,
    test_asset_basic_data,
    test_lot_data
)

# Config with info about API
config = {
    "url": "https://lb.api-sandbox.registry.ea.openprocurement.net",
    "version": 0,
    "token": "b31ef66eabcc44e3b5a5347b57539f49",
    "auction_url": "https://lb.api-sandbox.ea.openprocurement.org",
    "auction_token": "e9c3ccb8e8124f26941d5f9639a4ebc3",
    "auction_version": 2.5
}

# Data for test
test_auction_data = {
    "title": u"футляри до державних нагород",
    "dgfID": u"219560",
    "dgfDecisionDate": u"2016-11-17",
    "dgfDecisionID": u"219560",
    "tenderAttempts": 1,
    "procuringEntity": test_organization,
    "status": "pending.verification",
    "value": {
        "amount": 100,
        "currency": u"UAH"
    },
    "minimalStep": {
        "amount": 35,
        "currency": u"UAH"
    },
    "auctionPeriod": {
        "startDate": (datetime.now() + timedelta(minutes=3)).isoformat()
    },
    "procurementMethodType": "dgfInsider",
    "procurementMethodDetails": 'quick, accelerator=1440'
}


class InternalTest(unittest.TestCase):
    '''
        Internal TestCase for openregistry correctness.
        openprocurement.client.python for request

        Test workflow, concierge(bot), convoy(bot) and
        check switching statuses
    '''

    def setUp(self):
        # Init client for 2 resources
        self.lots_client = LotsClient(
            key=config['token'],
            host_url=config['url'],
            api_version=config['version']
        )
        self.assets_client = AssetsClient(
            key=config['token'],
            host_url=config['url'],
            api_version=config['version']
        )
        self.auctions_client = APIResourceClient(
            resource="auctions",
            key=config['auction_token'],
            host_url=config['auction_url'],
            api_version=config['auction_version']
        )

    def test_01_general_workflow(self):
        '''
            Create two assets and move them to pending status
            Create lot with this assets and move to verification status
            Create procedure from lot
            Check auction is unsuccessful and lot is active.salable
            Move lot to dissolved status and check assets pending status
        '''

        # Create assets =======================================================
        assets = []
        assets.append(self.assets_client.create_resource_item({
            "data": test_asset_basic_data
        }))
        assets.append(self.assets_client.create_resource_item({
            "data": test_asset_basic_data
        }))
        self.assertNotEqual(assets[0].data.id,
                            assets[1].data.id)
        self.assertEqual(assets[0].data.status, 'draft')
        self.assertEqual(assets[1].data.status, 'draft')

        print "Successfully created assets [{}, {}]".format(assets[0].data.id,
                                                           assets[1].data.id)

        # Move assets to pending ==============================================
        for asset in assets:
            asset_id = asset.data.id
            self.assets_client.patch_resource_item(asset.data.id, {"data": {"status": "pending"}}, asset.access.token)
            print "Move asset({}) to pending status".format(asset_id)
            self.assertEqual(self.assets_client.get_asset(asset_id).data.status,
                             "pending")

        # Create lot ==========================================================
        test_lot_data['assets'] = [assets[0].data.id,
                                   assets[1].data.id]
        lot = self.lots_client.create_resource_item({
            "data": test_lot_data
        })
        self.assertEqual(lot.data.status, 'draft')
        print "Successfully created lot {}".format(lot.data.id)
        # Move lot to Pending =================================================
        self.lots_client.patch_resource_item(lot.data.id, {"data": {"status": "pending"}}, lot.access.token)

        print "Successfully move lot {} to pending".format(lot.data.id)
        # Move lot to Verification ============================================
        self.lots_client.patch_resource_item(lot.data.id, {"data": {"status": "verification"}}, lot.access.token)
        print "Successfully move lot {} to verification".format(lot.data.id)
        # Check assets and lot statuses =======================================
        print "Waiting for Concierge ..."
        for i in range(15):
            time.sleep(i)  # Waiting for concierge
            lot_status = self.lots_client.get_lot(lot.data.id).data.status
            if lot_status != "verification":
                break

        upd_lot = self.lots_client.get_lot(lot.data.id).data
        self.assertEqual(upd_lot.status, "active.salable")
        for asset in upd_lot.assets:
            upd_asset = self.assets_client.get_asset(asset).data
            self.assertEqual(upd_asset.status, "active")
            self.assertEqual(upd_asset.relatedLot, upd_lot.id)

        print "Concierge move lot to active.salable and assets to active!"


        test_auction_data['merchandisingObject'] = lot.data.id

        auction = self.auctions_client.create_resource_item({
            "data": test_auction_data
        })
        self.assertEqual(auction.data.status, 'pending.verification')

        print "Successfully created auction {}".format(auction)

        print "Waiting for Convoy ..."
        for i in range(50):
            time.sleep(i)  # Waiting for convoy
            upd_asset = self.auctions_client.get_resource_item(auction.data.id).data

            if upd_asset.status == "active.tendering":
                break

        upd_auction = self.auctions_client.get_resource_item(auction.data.id).data
        self.assertEqual(upd_auction.status, "active.tendering")

        print "Waiting for UNS ..."
        while True:
            time.sleep(1)  # Waiting for convoy
            upd_asset = self.auctions_client.get_resource_item(auction.data.id).data

            if upd_asset.status != "active.tendering":
                break

        print "Waiting for convoy ..."
        while True:
            time.sleep(1)  # Waiting for convoy
            lot_status = self.lots_client.get_lot(lot.data.id).data.status

            if lot_status == "active.salable":
                break

        print "Convoy has done his work!"

        # Move lot to dissolved status ========================================
        self.lots_client.patch_resource_item(lot.data.id, {"data": {"status": "dissolved"}}, lot.access.token)
        lot_status = self.lots_client.get_lot(lot.data.id).data.status
        self.assertEqual(lot_status, "dissolved")
        print "Successfully move lot {} to dissolved".format(lot.data.id)

        # Check assets status

        print "Waiting for Concierge ..."
        for i in range(15):
            time.sleep(i)  # Waiting for concierge
            upd_asset = self.assets_client.get_asset(assets[0].data.id).data

            if upd_asset.status != "active":
                break

        for asset in assets:
            upd_asset = self.assets_client.get_asset(asset.data.id).data
            self.assertEqual(upd_asset.status, "pending")

        print "Concierge has done his work!"


if __name__ == '__main__':
    unittest.main()
