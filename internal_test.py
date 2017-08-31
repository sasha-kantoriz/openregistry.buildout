# -*- coding: utf-8 -*-
import unittest
import time

from openprocurement_client.registry_client import LotsClient, AssetsClient, APIBaseClient


# Config with info about API
config = {
    "url": "https://lb.api-sandbox.registry.ea.openprocurement.net",
    "version": 0,
    "token": "",
    "auction_url": "https://lb.api-sandbox.ea.openprocurement.org",
    "auction_token": "",
    "auction_version": 2.5
}

# Data for test
test_Custodian = {
    "name": u"Державне управління справами",
    "identifier": {
        "scheme": u"UA-EDR",
        "id": u"00037256",
        "uri": u"http://www.dus.gov.ua/"
    },
    "address": {
        "countryName": u"Україна",
        "postalCode": u"01220",
        "region": u"м. Київ",
        "locality": u"м. Київ",
        "streetAddress": u"вул. Банкова, 11, корпус 1"
    },
    "contactPoint": {
        "name": u"Державне управління справами",
        "telephone": u"0440000000"
    }
}

test_procuringEntity = test_Custodian.copy()
test_auction_data = {
    "title": u"футляри до державних нагород",
    "dgfID": u"219560",
    "dgfDecisionDate": u"2016-11-17",
    "dgfDecisionID": u"219560",
    "tenderAttempts": 1,
    "procuringEntity": test_procuringEntity,
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
        "startDate": "2017-08-28T19:20:37.363793+03:00"
    },
    "procurementMethodType": "dgfInsider",
    "procurementMethodDetails": 'quick, accelerator=1440'
}

test_asset_data = {
    "title": u"Земля для космодрому",
    "assetType": "basic",
    "assetCustodian": test_Custodian,
    "classification": {
        "scheme": u"CPV",
        "id": u"37452200-3",
        "description": u"Земельні ділянки"
    },
    "unit": {
        "name": u"item",
        "code": u"44617100-9"
    },
    "quantity": 5,
    "address": {
        "countryName": u"Україна",
        "postalCode": "79000",
        "region": u"м. Київ",
        "locality": u"м. Київ",
        "streetAddress": u"вул. Банкова 1"
    },
    "value": {
        "amount": 100,
        "currency": u"UAH"
    },
}

test_lot_data = {
    "title": u"Тестовий лот",
    "description": u"Щось там тестове",
    "lotType": "basic",
    "lotCustodian": test_Custodian,
    "assets": []
}


class ConciergeTest(unittest.TestCase):
    '''
        Internal Test for concierge(bot) correctness.
        openprocurement.client.python for request
        Create 2 assets and connect this assets to created lot
        Move lot to dissolved and check assets status
    '''
    # Declare test data

    def setUp(self):
        # Init client for 2 resources
        self.lots_client = LotsClient(
            resource="lots",
            key=config['token'],
            host_url=config['url'],
            api_version=config['version']
        )
        self.assets_client = AssetsClient(
            resource="assets",
            key=config['token'],
            host_url=config['url'],
            api_version=config['version']
        )
        self.auctions_client = APIBaseClient(
            resource="auctions",
            key=config['auction_token'],
            host_url=config['auction_url'],
            api_version=config['auction_version']
        )

    def test_01_concierge(self):
        '''
            Test workflow
            Create two assets and move them to pending status
            Create lot with this assets and move to verification status
            Check statuses
        '''
        # Create assets =======================================================

        assets = []
        assets.append(self.assets_client.create_resource_item({
            "data": test_asset_data
        }))
        assets.append(self.assets_client.create_resource_item({
            "data": test_asset_data
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
            self.assets_client.patch_resource_item({
                "access": {
                    "token": asset.access.token
                },
                "data": {
                    "id": asset_id,
                    "status": "pending"
                }
            })
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
        self.lots_client.patch_resource_item({
            "access": {
                "token": lot.access.token
            },
            "data": {
                "id": lot.data.id,
                "status": "pending"
            }
        })
        print "Successfully move lot {} to pending".format(lot.data.id)
        # Move lot to Verification ============================================
        self.lots_client.patch_resource_item({
            "access": {
                "token": lot.access.token
            },
            "data": {
                "id": lot.data.id,
                "status": "verification"
            }
        })
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

        # print "Convoy has done his work!"
        #
        # # Move lot to dissolved status ========================================
        # self.lots_client.patch_resource_item({
        #     "access": {
        #         "token": lot.access.token
        #     },
        #     "data": {
        #         "id": lot.data.id,
        #         "status": "dissolved"
        #     }
        # })
        # lot_status = self.lots_client.get_lot(lot.data.id).data.status
        # self.assertEqual(lot_status, "dissolved")
        # print "Successfully move lot {} to dissolved".format(lot.data.id)
        #
        # # Check assets status
        #
        # print "Waiting for Concierge ..."
        # for i in range(15):
        #     time.sleep(i)  # Waiting for concierge
        #     upd_asset = self.assets_client.get_asset(assets[0].data.id).data
        #
        #     if upd_asset.status != "active":
        #         break
        #
        # for asset in assets:
        #     upd_asset = self.assets_client.get_asset(asset.data.id).data
        #     self.assertEqual(upd_asset.status, "pending")
        #
        # print "Concierge has done his work!"

if __name__ == '__main__':
    unittest.main()
