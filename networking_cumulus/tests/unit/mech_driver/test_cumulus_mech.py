# Copyright 2016,2018 Cumulus Networks
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

import threading

from neutron.tests.unit import testlib_api

from networking_cumulus.mech_driver import driver as cumulus_driver
from networking_cumulus import version_abstract as va

TENANT_ID = 'cn_test_tenant_id'
NETWORK_NAME = 'cn_test_network'
NETWORK_ID = 'cn_test_network_id'
PORT_ID = 'cn_test_port_id'
VLAN_ID = 1000
HOST_NAME = 'cn_test_host'
ORIG_HOST_NAME = 'cn_test_orig_host'
DEVICE_ID = 'cn_test_device_id'
DEVICE_OWNER = va.const.DEVICE_OWNER_DHCP
BRIDGE_NAME = 'br1000'
SWITCH_ID = '192.168.2.210'


class CumulusMechanismDriverTestCase(testlib_api.SqlTestCase):
    """Main test cases for Cumulus Mechanism driver.

    Tests all mechanism driver APIs supported by Cumulus Driver. It invokes
    all the APIs as they would be invoked in real world scenarios and
    verifies the functionality.
    """
    def setUp(self):
        super(CumulusMechanismDriverTestCase, self).setUp()
        cumulus_driver.db = mock.MagicMock()
        self.driver = cumulus_driver.CumulusMechanismDriver()
        self.driver.switches = {SWITCH_ID}
        self.driver.switch_info[SWITCH_ID, 'spf_enable'] = True
        self.driver.switch_info[SWITCH_ID, 'new_bridge'] = False
        self.driver.sync_thread_lock = threading.Lock()

    def tearDown(self):
        super(CumulusMechanismDriverTestCase, self).tearDown()
        self.driver.stop_sync_thread()

    def test_create_network_precommit(self):
        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        self.driver.create_network_precommit(network_context)
        bridge_name = self.driver.get_bridge_name(NETWORK_ID,
                                                  self.driver.new_bridge)

        expected_calls = [
            mock.call.db_create_network(TENANT_ID,
                                        NETWORK_ID,
                                        VLAN_ID,
                                        bridge_name)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_delete_network_postcommit(self):
        cumulus_driver.db.db_get_bridge_name.return_value = \
            self.driver.get_bridge_name(NETWORK_ID,
                                        self.driver.new_bridge)
        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        self.driver.delete_network_postcommit(network_context)
        expected_calls = [
            mock.call.db_delete_network(TENANT_ID, NETWORK_ID)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_create_port_precommit(self):

        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        port_context = get_port_context(TENANT_ID,
                                        NETWORK_ID,
                                        DEVICE_ID,
                                        network_context,
                                        PORT_ID,
                                        DEVICE_OWNER,
                                        HOST_NAME,
                                        'ACTIVE')

        cumulus_driver.db.db_get_bridge_name.return_value = BRIDGE_NAME

        host_id = port_context.current['binding:host_id']
        port_id = port_context.current['id']
        self.driver.create_port_precommit(port_context)

        expected_calls = [
            mock.call.db_get_bridge_name(TENANT_ID, NETWORK_ID),
        ]
        expected_calls += [
            mock.call.db_create_port(TENANT_ID,
                                     NETWORK_ID,
                                     port_id,
                                     host_id,
                                     DEVICE_ID,
                                     BRIDGE_NAME,
                                     SWITCH_ID,
                                     VLAN_ID)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_create_port_postcommit(self):

        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        port_context = get_port_context(TENANT_ID,
                                        NETWORK_ID,
                                        DEVICE_ID,
                                        network_context,
                                        PORT_ID,
                                        DEVICE_OWNER,
                                        HOST_NAME,
                                        'ACTIVE')

        network = FakeCumulusNetworks(NETWORK_ID,
                                      TENANT_ID,
                                      VLAN_ID,
                                      BRIDGE_NAME)
        cumulus_driver.db.db_get_network.return_value = network

        self.driver.create_port_postcommit(port_context)

        expected_calls = [
            mock.call.db_get_network(TENANT_ID, NETWORK_ID)
        ]

        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_update_port_postcommit(self):
        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        port_context = get_port_update_context(TENANT_ID,
                                               NETWORK_ID,
                                               DEVICE_ID,
                                               network_context,
                                               PORT_ID,
                                               DEVICE_OWNER,
                                               HOST_NAME,
                                               ORIG_HOST_NAME,
                                               'ACTIVE')
        network = FakeCumulusNetworks(NETWORK_ID,
                                      TENANT_ID,
                                      VLAN_ID,
                                      BRIDGE_NAME)
        cumulus_driver.db.db_get_network.return_value = network

        db_port = FakeCumulusPorts(PORT_ID,
                                   TENANT_ID,
                                   NETWORK_ID,
                                   DEVICE_ID,
                                   SWITCH_ID,
                                   BRIDGE_NAME,
                                   HOST_NAME,
                                   VLAN_ID)
        cumulus_driver.db.db_get_port.return_value = db_port

        cumulus_driver.db.db_get_seg_type.return_value = False

        self.driver.update_port_postcommit(port_context)
        expected_calls = [
            mock.call.db_get_network(TENANT_ID,
                                     NETWORK_ID),
            mock.call.db_get_port(NETWORK_ID,
                                  PORT_ID,
                                  SWITCH_ID,
                                  HOST_NAME),
            mock.call.db_update_port(TENANT_ID,
                                     NETWORK_ID,
                                     PORT_ID,
                                     HOST_NAME,
                                     DEVICE_ID,
                                     BRIDGE_NAME,
                                     SWITCH_ID,
                                     VLAN_ID),
            mock.call.db_get_seg_type(NETWORK_ID),
            mock.call.db_delete_port(NETWORK_ID,
                                     PORT_ID,
                                     SWITCH_ID,
                                     ORIG_HOST_NAME),
        ]
        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_delete_port_postcommit(self):
        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        port_context = get_port_context(TENANT_ID,
                                        NETWORK_ID,
                                        DEVICE_ID,
                                        network_context,
                                        PORT_ID,
                                        DEVICE_OWNER,
                                        HOST_NAME,
                                        'ACTIVE')

        network = FakeCumulusNetworks(NETWORK_ID,
                                      TENANT_ID,
                                      VLAN_ID,
                                      BRIDGE_NAME)
        cumulus_driver.db.db_get_network.return_value = network

        db_port = FakeCumulusPorts(PORT_ID,
                                   TENANT_ID,
                                   NETWORK_ID,
                                   DEVICE_ID,
                                   SWITCH_ID,
                                   BRIDGE_NAME,
                                   HOST_NAME,
                                   VLAN_ID)
        cumulus_driver.db.db_get_port.return_value = db_port

        cumulus_driver.db.db_get_seg_type.return_value = False

        self.driver.delete_port_postcommit(port_context)

        expected_calls = [
            mock.call.db_delete_port(NETWORK_ID,
                                     PORT_ID,
                                     SWITCH_ID,
                                     HOST_NAME)
        ]
        cumulus_driver.db.assert_has_calls(expected_calls)

    def test_bind_port(self):
        network_context = get_network_context(TENANT_ID,
                                              NETWORK_ID,
                                              NETWORK_NAME,
                                              VLAN_ID,
                                              False)

        port_context = get_port_context(TENANT_ID,
                                        NETWORK_ID,
                                        DEVICE_ID,
                                        network_context,
                                        PORT_ID,
                                        DEVICE_OWNER,
                                        HOST_NAME,
                                        'ACTIVE')

        self.driver.bind_port(port_context)


def get_network_context(tenant_id, net_id, net_name,
                        segmentation_id, shared):
    network = {'id': net_id,
               'tenant_id': tenant_id,
               'name': net_name,
               'shared': shared,
               'provider:network_type': va.const.TYPE_VLAN,
               'provider:segmentation_id': segmentation_id}

    network_segments = [{'segmentation_id': segmentation_id,
                         'physical_network': u'default',
                         'id': 'segment-id-for-%s' % segmentation_id,
                         'network_type': va.const.TYPE_VXLAN}]

    return FakeNetworkContext(network, network_segments,
                              network)


def get_port_context(tenant_id, net_id, device_id, network, port_id,
                     device_owner, host, status='ACTIVE',
                     dynamic_segment=None):
    port = {'admin_state_up': True,
            'device_id': device_id,
            'device_owner': device_owner,
            'binding:host_id': host,
            'binding:vnic_type': 'normal',
            'binding:profile': [],
            'tenant_id': tenant_id,
            'id': port_id,
            'network_id': net_id,
            'name': '',
            'status': status,
            'fixed_ips': [],
            'security_groups': None}

    binding_levels = []

    network_segments = network.network_segments

    if dynamic_segment:
        network_segments.append(dynamic_segment)
    for level, segment in enumerate(network_segments):
        binding_levels.append(FakePortBindingLevel(port['id'],
                                                   level,
                                                   'vendor-1',
                                                   segment['id'],
                                                   host))

    return FakePortContext(port, dict(port), network, port['status'],
                           binding_levels)


def get_port_update_context(tenant_id, net_id, device_id, network, port_id,
                            device_owner, host, orig_host, status='ACTIVE',
                            dynamic_segment=None):
    port = {'admin_state_up': True,
            'device_id': device_id,
            'device_owner': device_owner,
            'binding:host_id': host,
            'binding:vnic_type': 'normal',
            'binding:profile': [],
            'tenant_id': tenant_id,
            'id': port_id,
            'network_id': net_id,
            'name': '',
            'status': status,
            'fixed_ips': [],
            'security_groups': None}

    orig_port = {'admin_state_up': True,
                 'device_id': device_id,
                 'device_owner': device_owner,
                 'binding:host_id': orig_host,
                 'binding:vnic_type': 'normal',
                 'binding:profile': [],
                 'tenant_id': tenant_id,
                 'id': port_id,
                 'network_id': net_id,
                 'name': '',
                 'status': status,
                 'fixed_ips': [],
                 'security_groups': None}

    binding_levels = []

    network_segments = network.network_segments

    if dynamic_segment:
        network_segments.append(dynamic_segment)
    for level, segment in enumerate(network_segments):
        binding_levels.append(FakePortBindingLevel(port['id'],
                                                   level,
                                                   'vendor-1',
                                                   segment['id'],
                                                   host))

    return FakePortContext(port, dict(orig_port), network, port['status'],
                           binding_levels)


class FakeNetworkContext(object):
    """To generate network context for testing purposes only."""

    def __init__(self, network, segments=None, original_network=None):
        self._network = network
        self._original_network = original_network
        self._segments = segments

    @property
    def current(self):
        return self._network

    @property
    def original(self):
        return self._original_network

    @property
    def network_segments(self):
        return self._segments


class FakePortContext(object):
    """To generate port context for testing purposes only."""

    def __init__(self, port, original_port, network, status,
                 binding_levels):
        self._plugin_context = None
        self._port = port
        self._original_port = original_port
        self._network_context = network
        self._status = status
        self._binding_levels = binding_levels
        self.is_admin = False
        self.is_advsvc = False
        self.tenant_id = port['tenant_id']
        self.project_id = port['tenant_id']
        self.segments_to_bind = [self._network_context.network_segments]

    @property
    def current(self):
        return self._port

    @property
    def original(self):
        return self._original_port

    @property
    def network(self):
        return self._network_context

    @property
    def host(self):
        return self._port.get(va.portbindings.HOST_ID)

    @property
    def original_host(self):
        return self._original_port.get(va.portbindings.HOST_ID)

    @property
    def status(self):
        return self._status

    @property
    def original_status(self):
        if self._original_port:
            return self._original_port['status']

    @property
    def binding_levels(self):
        if self._binding_levels:
            return [{
                va.api.BOUND_DRIVER: level.driver,
                va.api.BOUND_SEGMENT:
                    self._expand_segment(level.segment_id)
            } for level in self._binding_levels]

    @property
    def top_bound_segment(self):
        return self._network_context._segments[0]

    @property
    def bottom_bound_segment(self):
        if self._binding_levels:
            return self._expand_segment(self._binding_levels[-1].segment_id)

    def _expand_segment(self, segment_id):
        for segment in self._network_context._segments:
            if segment[va.api.ID] == segment_id:
                return segment

    @property
    def allocate_dynamic_segment(self, segment):
        pass

    @property
    def continue_binding(self, segment_id, next_segments_to_bind):
        pass


class FakePortBindingLevel(object):
    """Port binding object for testing purposes only."""

    def __init__(self, port_id, level, driver, segment_id, host_id):
        self.port_id = port_id
        self.level = level
        self.driver = driver
        self.segment_id = segment_id
        self.host = host_id


class FakeCumulusNetworks(object):
    """Represents a binding of network id to cumulus bridge."""

    def __init__(self, network_id=None, tenant_id=None, segmentation_id=None,
                 bridge_name=None):
        self.network_id = network_id
        self.tenant_id = tenant_id
        self.bridge_name = bridge_name
        self.segmentation_id = segmentation_id


class FakeCumulusPorts(object):

    def __init__(self, port_id=None, tenant_id=None, network_id=None,
                 device_id=None, server_id=None, bridge_name=None,
                 host_id=None, vni=None):
        self.port_id = port_id
        self.tenant_id = tenant_id
        self.network_id = network_id
        self.device_id = device_id
        self.server_id = server_id
        self.bridge_name = bridge_name
        self.host_id = host_id
        self.vni = vni
