# Copyright (C) 2017-2019 Pier Carlo Chiodi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import yaml
import shutil
import tempfile
import unittest

from pierky.arouteserver.arin_db_dump import ARINWhoisDBDump
from pierky.arouteserver.config.general import ConfigParserGeneral
from pierky.arouteserver.irrdb import ASSet, RSet
from pierky.arouteserver.last_version import LastVersion
from pierky.arouteserver.peering_db import PeeringDBNet, PeeringDBIXList
from pierky.arouteserver.ripe_rpki_cache import RIPE_RPKI_ROAs

cache_dir = None
cache_cfg = {
    "cache_dir": None
}


class TestExternalResources(unittest.TestCase):

    def setUp(self):
        global cache_dir
        cache_dir = tempfile.mkdtemp(suffix="arouteserver_unittest")
        cache_cfg["cache_dir"] = cache_dir

    def tearDown(self):
        shutil.rmtree(cache_dir, ignore_errors=True)

    def test_peeringdb(self):
        """External resources: PeeringDB, max-prefix and AS-SET"""
        net = PeeringDBNet(3333, **cache_cfg)
        net.load_data()
        self.assertTrue(net.info_prefixes4 > 0)
        self.assertTrue(net.info_prefixes6 > 0)
        self.assertEqual(net.irr_as_sets, ["AS-RIPENCC"])

    def test_arin_db_dump(self):
        """External resources: ARIN Whois database dump"""
        cfg = ConfigParserGeneral()
        url = cfg.get_schema()["cfg"]["filtering"]["irrdb"]["use_arin_bulk_whois_data"]["source"].default
        db_dump = ARINWhoisDBDump(source=url, **cache_cfg)
        db_dump.load_data()
        self.assertTrue(len(db_dump.whois_records) > 0)

    def test_ixf_db(self):
        """External resources: PeeringDB IX list"""
        ixp_list = PeeringDBIXList()
        ixp_list.load_data()
        self.assertTrue(len(ixp_list.ixp_list) > 0)

    def test_last_version(self):
        """External resources: last version via PyPI"""
        last_ver = LastVersion(**cache_cfg)
        last_ver.load_data()
        ver = last_ver.last_version
        self.assertTrue(int(ver.split(".")[0]) >= 0)
        self.assertTrue(int(ver.split(".")[1]) >= 17)

    def _test_rpki_roas_per_provider(self, provider):
        cfg = ConfigParserGeneral()
        urls = cfg.get_schema()["cfg"]["rpki_roas"]["ripe_rpki_validator_url"].default
        for url in urls:
            if provider in url:
                rpki_roas = RIPE_RPKI_ROAs(ripe_rpki_validator_url=[url], **cache_cfg)
                break
        rpki_roas.load_data()
        self.assertTrue(len(rpki_roas.roas) > 0)
        self.assertTrue(any([r for r in rpki_roas.roas["roas"] if r["prefix"] == "193.0.0.0/21"]))

        allowed_per_ta = {}

        allowed_tas = cfg.get_schema()["cfg"]["rpki_roas"]["allowed_trust_anchors"].default
        for roa in rpki_roas.roas["roas"]:
            ta = roa["ta"]
            if ta not in allowed_per_ta:
                allowed_per_ta[ta] = 0
            if roa["ta"] in allowed_tas:
                allowed_per_ta[ta] += 1

        tas_with_allowed_roas = 0
        for ta in allowed_per_ta:
            if allowed_per_ta[ta] > 0:
                tas_with_allowed_roas += 1

        self.assertTrue(tas_with_allowed_roas >= 4)

    def test_rpki_roas_ripe(self):
        """External resources: RPKI ROAs, RIPE"""
        self._test_rpki_roas_per_provider("ripe.net")

    def test_rpki_roas_ntt(self):
        """External resources: RPKI ROAs, NTT"""
        self._test_rpki_roas_per_provider("ntt.net")

    def test_asset(self):
        """External resources: ASNs from AS-SET via bgpq4"""
        asset = ASSet(["AS-RIPENCC"], bgpq4_path="bgpq4", **cache_cfg)
        asset.load_data()
        self.assertTrue(len(asset.asns) > 0)
        self.assertTrue(3333 in asset.asns)

    def test_rset(self):
        """External resources: prefixes from AS-SET via bgpq4"""
        rset = RSet(["AS-RIPENCC"], 4, False, bgpq4_path="bgpq4", **cache_cfg)
        rset.load_data()
        self.assertTrue(len(rset.prefixes) > 0)
        self.assertTrue(any([p for p in rset.prefixes if p["prefix"] == "193.0.0.0"]))
