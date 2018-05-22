# Copyright 2018 Cumulus Networks
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from distutils.version import StrictVersion

from neutron import version


# Some constants and verifier functions have been deprecated but are still
# used by earlier releases of neutron. In order to maintain
# backwards-compatibility with stable/mitaka this will act as a translator
# that passes constants and functions according to version number.

NEUTRON_VERSION = StrictVersion(str(version.version_info))
NEUTRON_NEWTON_VERSION = StrictVersion('9.0.0')
NEUTRON_OCATA_VERSION = StrictVersion('10.0.0')
NEUTRON_PIKE_VERSION = StrictVersion('11.0.0')

if NEUTRON_VERSION > NEUTRON_NEWTON_VERSION:
    from neutron_lib import constants as const  # noqa
else:
    from neutron.plugins.common import constants as const  # noqa

if NEUTRON_VERSION > NEUTRON_OCATA_VERSION:
    from neutron_lib.api.definitions import portbindings  # noqa
else:
    from neutron.extensions import portbindings  # noqa

if NEUTRON_VERSION > NEUTRON_PIKE_VERSION:
    from neutron.db import api as db_api
    from neutron_lib.plugins.ml2 import api  # noqa

    def get_db_read_sess():
        return db_api.get_reader_session()

    def get_db_write_sess():
        return db_api.get_writer_session()
else:
    from neutron.db import api as db_api
    from neutron.plugins.ml2 import driver_api as api  # noqa

    def get_db_read_sess():
        return db_api.get_session()

    def get_db_write_sess():
        return db_api.get_session()
