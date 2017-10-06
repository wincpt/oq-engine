# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2017 GEM Foundation
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
import numpy
from openquake.calculators import base, event_based_risk as ebr


def ebrisk(riskinput, riskmodel, param, monitor):
    """
    :param riskinput:
        a :class:`openquake.risklib.riskinput.RiskInput` object
    :param riskmodel:
        a :class:`openquake.risklib.riskinput.CompositeRiskModel` instance
    :param param:
        a dictionary of parameters
    :param monitor:
        :class:`openquake.baselib.performance.Monitor` instance
    :returns:
        a dictionary with an array losses of shape (A, E, R, L * I)
    """
    riskinput.hazard_getter.init()
    assetcol = param['assetcol']
    all_eids = riskinput.hazard_getter.eids
    A = len(assetcol)
    E = len(all_eids)
    I = param['insured_losses'] + 1
    L = len(riskmodel.lti)
    R = riskinput.hazard_getter.num_rlzs
    eidx = dict(zip(all_eids, range(E)))
    result = dict(losses=numpy.zeros((A, E, R, L * I), ebr.F32),
                  eids=all_eids, aids=getattr(riskinput, 'aids', None))
    for outs in riskmodel.gen_outputs(riskinput, monitor, assetcol):
        r = outs.r
        for l, out in enumerate(outs):
            if out is None:  # for GMFs below the minimum_intensity
                continue
            loss_ratios, eids = out
            indices = numpy.array([eidx[eid] for eid in eids])  # length E'
            loss_type = riskmodel.loss_types[l]
            for asset, ratios in zip(outs.assets, loss_ratios):
                aid = asset.ordinal
                losses = ratios * asset.value(loss_type)  # shape (E', I)
                for i in range(I):
                    li = l + L * i
                    result['losses'][aid, indices, r, li] = losses[:, i]
    # store info about the GMFs
    result['gmdata'] = riskinput.gmdata
    return result


@base.calculators.add('ebrisk')
class EbriskCalculator(ebr.EbriskCalculator):
    """
    Event based PSHA calculator generating the asset loss table
    """
    pre_calculator = 'event_based_rupture'
    is_stochastic = True
    core_task = ebrisk

    def update(self, name, attr, value):
        orig_value = self.datastore.get_attr(name, attr, 0)
        self.datastore.set_attrs(name, **{attr: orig_value + value})

    def save_losses(self, dic, offset=0):
        """
        Save the event loss tables incrementally.

        :param dic:
            dictionary with losses, eids, aids
        :param offset:
            realization offset
        """
        bytes_per_block = 2 + self.L * self.I * 4
        with self.monitor('saving asset_loss_table', autoflush=True):
            aids = dic.pop('aids') or range(len(self.assetcol))
            eids = dic.pop('eids')
            losses = dic.pop('losses')  # shape (A, E, R, LI)
            alt = self.datastore['asset_loss_table']
            nbytes = 0
            for aid, alosses in zip(aids, losses):
                for eid, elosses in zip(eids, alosses):
                    lst = [((r + offset, llosses))
                           for r, llosses in enumerate(elosses)
                           if llosses.sum()]
                    if lst:
                        nbytes += 8 + bytes_per_block * len(lst)
                        data = numpy.array(lst, self.alt_dt)
                        alt[aid, self.eidx[eid]] = data
            self.update('asset_loss_table', 'nbytes', nbytes)
            self.taskno += 1
            self.start += losses.shape[2]  # num_rlzs

    def post_execute(self, num_events):
        shp = (self.A, self.R, self.L * self.I)
        losses_by_asset = numpy.zeros(shp, ebr.F32)
        alt = self.datastore['asset_loss_table']
        for aid, all_rlz_losses in enumerate(alt):
            for rlz_losses in all_rlz_losses:
                for rlz, losses in rlz_losses:
                    losses_by_asset[aid, rlz] += losses
        self.datastore['losses_by_asset'] = losses_by_asset
