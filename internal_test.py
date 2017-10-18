# -*- coding: utf-8 -*-
import unittest
import time
from datetime import datetime, timedelta

from openprocurement_client.resources.assets import AssetsClient
from openprocurement_client.resources.lots import LotsClient
from openprocurement_client.clients import APIResourceClient

from openregistry.api.tests.blanks.json_data import (
    test_organization,
    test_asset_claimrights_data as test_asset_basic_data,
    test_lot_data
)

# Config with info about API
# config = {
#     "url": "https://lb.api-sandbox.registry.ea.openprocurement.net",
#     "version": 0,
#     "token": "",
#     "auction_url": "https://lb.api-sandbox.ea.openprocurement.org",
#     "auction_token": "",
#     "auction_version": 2.5
# }
config = {
    "url": "http://127.0.0.1:6543",
    "version": 0.1,
    "token": "broker",
    "ds": {
        "host_url": "http://127.0.0.1:8008",
        "auth_ds": ["broker", "9dd52697e3a0433b976d5988aaf693be"]
    }
}

# Data for test
test_asset_basic_data['mode'] = 'test'
test_lot_data['mode'] = 'test'

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
            api_version=config['version'],
            ds_config=config['ds']
        )
        self.assets_client = AssetsClient(
            key=config['token'],
            host_url=config['url'],
            api_version=config['version'],
            ds_config=config['ds']
        )
        # self.auctions_client = APIResourceClient(
        #     resource="auctions",
        #     key=config['auction_token'],
        #     host_url=config['auction_url'],
        #     api_version=config['auction_version']
        # )

    def ensure_resource_status(self, get_resource, id, status, *args, **kwargs):
        '''
            Wait for switching resource's status
        '''

        times = kwargs.get("times", 20)
        waiting_message = kwargs.get("waiting_message",
                                     "Waiting for resource's ({}) '{}' status".format(id, status))

        for i in reversed(range(times)):
            time.sleep(i)

            resource = get_resource(id).data
            if resource.status == status:
                break
            else:
                print waiting_message

        resource = get_resource(id).data
        self.assertEqual(resource.status, status)

        return resource

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
            self.assets_client.patch_asset(asset.data.id, {"data": {"status": "pending"}}, asset.access.token)
            self.assertEqual(self.assets_client.get_asset(asset_id).data.status,
                             "pending")

        print "Moved assets to 'pending' status"

        # Create lot ==========================================================
        test_lot_data['assets'] = [assets[0].data.id,
                                   assets[1].data.id]
        lot = self.lots_client.create_resource_item({
            "data": test_lot_data
        })
        self.assertEqual(lot.data.status, 'draft')

        print "Successfully created lot [{}]".format(lot.data.id)

        # Move lot to Pending =================================================
        self.lots_client.patch_lot(lot.data.id, {"data": {"status": "pending"}}, lot.access.token)
        self.assertEqual(self.lots_client.get_lot(lot.data.id).data.status, "pending")

        print "Moved lot to 'pending' status"

        # Move lot to Verification ============================================
        self.lots_client.patch_lot(lot.data.id, {"data": {"status": "verification"}}, lot.access.token)
        self.assertEqual(self.lots_client.get_lot(lot.data.id).data.status, "verification")

        print "Moved lot to 'verification' status"

        # Check lot and assets statuses =======================================
        upd_lot = self.ensure_resource_status(
            self.lots_client.get_lot,
            lot.data.id, "active.salable",
            waiting_message="Waiting for Concierge ..."
        )
        for asset in upd_lot.assets:
            upd_asset = self.assets_client.get_asset(asset).data
            self.assertEqual(upd_asset.status, "active")
            self.assertEqual(upd_asset.relatedLot, upd_lot.id)

        print "Concierge has moved lot to 'active.salable' and assets to 'active' statuses"

        # Create auction ======================================================
        # test_auction_data['merchandisingObject'] = lot.data.id
        #
        # auction = self.auctions_client.create_resource_item({
        #     "data": test_auction_data
        # })
        # self.assertEqual(auction.data.status, 'pending.verification')
        #
        # print "Successfully created auction [{}]".format(auction.data.id)

        # Check auction and lot statuses ======================================
        # self.ensure_resource_status(
        #     self.auctions_client.get_resource_item,
        #     auction.data.id, "active.tendering",
        #     waiting_message="Waiting for Convoy ..."
        # )
        #
        # self.assertEqual(self.lots_client.get_lot(lot.data.id).data.status,
        #                  "active.auction")
        #
        # print "Convoy has moved lot to 'active.auction' status"

        # Check auction finished ==============================================
        # self.ensure_resource_status(
        #     self.auctions_client.get_resource_item,
        #     auction.data.id, "unsuccessful",
        #     times=35,
        #     waiting_message="Waiting for UNS ..."
        # )
        #
        # print "Switched auction to 'unsuccessful' status"

        # Check lot status ====================================================
        # self.ensure_resource_status(
        #     self.lots_client.get_lot,
        #     lot.data.id, "active.salable",
        #     waiting_message="Waiting for Convoy ..."
        # )
        #
        # print "Convoy has moved lot to 'active.salable' status and done his work!"

        # Move lot to dissolved status ========================================
        self.lots_client.patch_lot(lot.data.id, {"data": {"status": "pending.dissolution"}}, lot.access.token)
        lot_status = self.lots_client.get_lot(lot.data.id).data.status
        self.assertEqual(lot_status, "pending.dissolution")

        print "Switched lot to 'pending.dissolution' status"

        # Check assets and lot status =========================================
        self.ensure_resource_status(
            self.lots_client.get_lot,
            lot.data.id, "dissolved",
            waiting_message="Waiting for Concierge ..."
        )

        for asset in assets:
            upd_asset = self.assets_client.get_asset(asset.data.id).data
            self.assertEqual(upd_asset.status, "pending")

        print "Concierge has moved assets to 'pending' status and done his work!"


if __name__ == '__main__':
    unittest.main()
