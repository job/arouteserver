# Copyright (C) 2017 Pier Carlo Chiodi
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

from ...base import LiveScenario

class PathHidingScenario(LiveScenario):
    __test__ = False

    MODULE_PATH = __file__
    RS_INSTANCE_CLASS = None
    CLIENT_INSTANCE_CLASS = None
    IP_VER = None

    CFG_GENERAL = None

    AS_SET = {
    }
    R_SET = {
    }

    @classmethod
    def _setup_instances(cls):
        cls.INSTANCES = [
            cls.RS_INSTANCE_CLASS(
                "rs",
                cls.DATA["rs_IPAddress"],
                [
                    (
                        cls._build_rs_cfg("bird", "main.j2", "rs.conf",
                                          cfg_general=cls.CFG_GENERAL),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
            cls.CLIENT_INSTANCE_CLASS(
                "AS1",
                cls.DATA["AS1_IPAddress"],
                [
                    (
                        cls._build_other_cfg("AS1.j2"),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
            cls.CLIENT_INSTANCE_CLASS(
                "AS2",
                cls.DATA["AS2_IPAddress"],
                [
                    (
                        cls._build_other_cfg("AS2.j2"),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
            cls.CLIENT_INSTANCE_CLASS(
                "AS3",
                cls.DATA["AS3_IPAddress"],
                [
                    (
                        cls._build_other_cfg("AS3.j2"),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
            cls.CLIENT_INSTANCE_CLASS(
                "AS4",
                cls.DATA["AS4_IPAddress"],
                [
                    (
                        cls._build_other_cfg("AS4.j2"),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
            cls.CLIENT_INSTANCE_CLASS(
                "AS101",
                cls.DATA["AS101_IPAddress"],
                [
                    (
                        cls._build_other_cfg("AS101.j2"),
                        "/etc/bird/bird.conf"
                    )
                ]
            ),
        ]

    def set_instance_variables(self):
        self.rs = self._get_instance_by_name("rs")
        self.AS1 = self._get_instance_by_name("AS1")
        self.AS2 = self._get_instance_by_name("AS2")
        self.AS3 = self._get_instance_by_name("AS3")
        self.AS4 = self._get_instance_by_name("AS4")
        self.AS101 = self._get_instance_by_name("AS101")
        
    def test_010_setup(self):
        """{}: instances setup"""
        pass

    def test_020_sessions_up(self):
        """{}: sessions are up"""
        self.session_is_up(self.rs, self.AS1)
        self.session_is_up(self.rs, self.AS2)
        self.session_is_up(self.rs, self.AS3)
        self.session_is_up(self.rs, self.AS4)
        self.session_is_up(self.AS1, self.AS101)
        self.session_is_up(self.AS2, self.AS101)

    def test_030_rs_receives_route_from_AS1_and_AS2(self):
        """{}: rs should receive prefix from both AS1 and AS2"""
        self.receive_route_from(self.rs, self.DATA["AS101_pref_ok1"], self.AS1,
                                as_path="1 101")
        self.receive_route_from(self.rs, self.DATA["AS101_pref_ok1"], self.AS2,
                                as_path="2 101 101 101 101")

    def test_031_rs_has_best_toward_AS1(self):
        """{}: rs should have best toward AS1"""
        self.receive_route_from(self.rs, self.DATA["AS101_pref_ok1"], self.AS1,
                                only_best=True)

    def test_032_AS1_do_not_announce_to_AS3_and_AS4(self):
        """{}: AS1 wants rs to not announce to AS3 and AS4"""
        self.receive_route_from(self.rs, self.DATA["AS101_pref_ok1"], self.AS1,
                                std_comms=["0:3", "0:4"])
        self.log_contains(self.rs, "prefix didn't pass control communities checks - NOT ANNOUNCING {} TO {{AS3}}".format(
            self.DATA["AS101_pref_ok1"]), {"AS3": self.AS3})
        self.log_contains(self.rs, "prefix didn't pass control communities checks - NOT ANNOUNCING {} TO {{AS4}}".format(
            self.DATA["AS101_pref_ok1"]), {"AS4": self.AS4})

class PathHidingScenario_MitigationOn(PathHidingScenario):
    __test__ = False

    CFG_GENERAL = "general_on.yml"

    def test_040_AS3_and_AS4_prefix_via_AS2(self):
        """{}: AS3 and AS4 receive prefix with sub-optimal path via AS2"""
        for inst in (self.AS3, self.AS4):
            self.receive_route_from(inst, self.DATA["AS101_pref_ok1"], self.rs,
                                    as_path="2 101 101 101 101", next_hop=self.AS2,
                                    std_comms=[])

    def test_041_AS3_and_AS4_no_prefix_via_AS1(self):
        """{}: AS3 and AS4 don't receive prefix via AS1"""
        for inst in (self.AS3, self.AS4):
            with self.assertRaises(AssertionError):
                self.receive_route_from(inst, self.DATA["AS101_pref_ok1"], self.rs,
                                        next_hop=self.AS1)

class PathHidingScenario_MitigationOff(PathHidingScenario):
    __test__ = False

    CFG_GENERAL = "general_off.yml"

    def test_050_AS3_prefix_not_received_by_AS3(self):
        """{}: AS3 does not receive prefix at all"""
        with self.assertRaises(AssertionError):
            self.receive_route_from(self.AS3, self.DATA["AS101_pref_ok1"])

    def test_051_AS4_receives_prefix_via_AS2_because_of_ADD_PATH(self):
        """{}: AS4 receives the prefix via AS2 because of ADD-PATH"""
        self.receive_route_from(self.AS4, self.DATA["AS101_pref_ok1"], self.rs,
                                as_path="2 101 101 101 101", next_hop=self.AS2,
                                std_comms=[])