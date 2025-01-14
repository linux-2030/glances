# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""ElasticSearch interface class."""

import sys
from datetime import datetime

from glances.logger import logger
from glances.exports.glances_export import GlancesExport

from elasticsearch import Elasticsearch, helpers
from elasticsearch import __version__ as elk_version


class Export(GlancesExport):

    """This class manages the ElasticSearch (ES) export module."""

    def __init__(self, config=None, args=None):
        """Init the ES export IF."""
        super(Export, self).__init__(config=config, args=args)

        # Mandatory configuration keys (additional to host and port)
        self.index = None

        # Load the ES configuration file
        self.export_enable = self.load_conf('elasticsearch', mandatories=['host', 'port', 'index'], options=[])
        if not self.export_enable:
            sys.exit(2)

        # Init the ES client
        self.client = self.init()

    def init(self):
        """Init the connection to the ES server."""
        if not self.export_enable:
            return None

        try:
            es = Elasticsearch(hosts=['{}:{}'.format(self.host, self.port)])
        except Exception as e:
            logger.critical("Cannot connect to ElasticSearch server %s:%s (%s)" % (self.host, self.port, e))
            sys.exit(2)
        else:
            logger.info("Connected to the ElasticSearch server %s:%s" % (self.host, self.port))

        return es

    def export(self, name, columns, points):
        """Write the points to the ES server."""
        logger.debug("Export {} stats to ElasticSearch".format(name))

        # Generate index name with the index field + current day
        index = '{}-{}'.format(self.index, datetime.utcnow().strftime("%Y.%m.%d"))

        # Create DB input
        # https://elasticsearch-py.readthedocs.io/en/master/helpers.html
        actions = []
        dt_now = datetime.utcnow().isoformat('T')
        action = {
            "_index": index,
            "_id": '{}.{}'.format(name, dt_now),
            "_type": 'glances-{}'.format(name),
            "_source": {"plugin": name, "timestamp": dt_now},
        }
        action['_source'].update(zip(columns, [str(p) for p in points]))
        actions.append(action)

        logger.debug("Exporting the following object to elasticsearch: {}".format(action))

        # Write input to the ES index
        try:
            helpers.bulk(self.client, actions)
        except Exception as e:
            logger.error("Cannot export {} stats to ElasticSearch ({})".format(name, e))
