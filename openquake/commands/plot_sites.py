# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2015-2018 GEM Foundation
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake. If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
import logging
import random
import numpy
from openquake.baselib import sap, datastore
from openquake.hazardlib.geo.utils import (
    cross_idl, angular_distance, KM_TO_DEGREES)


class Source:
    def __init__(self, info):
        self.lons, self.lats = info['lonlats'].reshape(2, -1)

    def get_rectangle(self, idl, maxdist):
        if idl:
            self.lons = self.lons % 360
        west, east = self.lons.min(), self.lons.max()
        south, north = self.lats.min(), self.lats.max()
        a1 = maxdist * KM_TO_DEGREES
        a2 = angular_distance(maxdist, north, south)
        return (west, south), west - east + 2 * a2, north - south + 2 * a1


@sap.Script
def plot_sites(calc_id=-1):
    """
    Plot the sites and the bounding boxes of the sources, enlarged by
    the maximum distance
    """
    # NB: matplotlib is imported inside since it is a costly import
    import matplotlib.pyplot as p
    from matplotlib.patches import Rectangle
    logging.basicConfig(level=logging.INFO)
    dstore = datastore.read(calc_id)
    oq = dstore['oqparam']
    sitecol = dstore['sitecol']
    lons, lats = sitecol.lons, sitecol.lats
    info = dstore['source_info'].value
    info = info[info['calc_time'] > 0]
    if len(info) > 100:
        logging.info('Sampling 100 sources of %d', len(info))
        info = random.Random(42).sample(info, 100)
    sources = [Source(rec) for rec in info]
    lonset = set(lons)
    for src in sources:
        lonset.update(src.lons)
    idl = cross_idl(min(lonset), max(lonset))
    rects = [src.get_rectangle(idl, oq.maximum_distance['default'])
             for src in sources]

    fig, ax = p.subplots()
    ax.grid(True)
    for src, (lonlat, width, height) in zip(sources, rects):
        ax.add_patch(Rectangle(lonlat, width, height, fill=False))
        # add a point to close the source polygon
        xs = numpy.append(src.lons, src.lons[0])
        ys = numpy.append(src.lats, src.lats[0])
        p.plot(xs, ys, marker='.')

    p.scatter(lons, lats, marker='+')
    p.show()


plot_sites.arg('calc_id', 'a computation id', type=int)
