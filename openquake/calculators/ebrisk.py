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
import h5py
from openquake.baselib.general import AccumDict
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
        a dictionary with an array of losses of shape (T, E, R, L * I)
    """
    riskinput.hazard_getter.init()
    assetcol = param['assetcol']
    all_eids = riskinput.hazard_getter.eids
    aids_by_tag = assetcol.aids_by_tag
    tags = assetcol.tags()
    T = len(aids_by_tag)
    E = len(all_eids)
    I = param['insured_losses'] + 1
    L = len(riskmodel.lti)
    R = riskinput.hazard_getter.num_rlzs
    eidx = dict(zip(all_eids, range(E)))
    losses = numpy.zeros((T, E, R, L * I), ebr.F32)
    result = dict(losses=losses,
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
                avalues = ratios * asset.value(loss_type)  # shape (E', I)
                for t, tag in enumerate(tags):
                    if aid in aids_by_tag[tag]:
                        for i in range(I):
                            losses[t, indices, r, l + L * i] += avalues[:, i]

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
        # 2 bytes per rlzi + 4 bytes per loss type
        bytes_per_block = 2 + self.L * self.I * 4
        with self.monitor('saving tag_loss_table', autoflush=True):
            eids = dic.pop('eids')
            losses = dic.pop('losses')  # shape (T, E, R, LI)
            tag_loss_table = self.datastore['tag_loss_table']
            nbytes = 0
            for t, tlosses in enumerate(losses):
                for eid, elosses in zip(eids, tlosses):
                    lst = [((r + offset, llosses))
                           for r, llosses in enumerate(elosses)
                           if llosses.sum()]
                    if lst:
                        # 8 bytes per vlen array + bytes per blocks
                        nbytes += 8 + bytes_per_block * len(lst)
                        data = numpy.array(lst, self.alt_dt)
                        tag_loss_table[self.eidx[eid], t] = data
            self.update('tag_loss_table', 'nbytes', nbytes)
            self.taskno += 1
            self.start += losses.shape[2]  # num_rlzs

    def post_execute(self, num_events):
        shp = (self.T, self.R, self.L * self.I)
        losses_by_tag = numpy.zeros(shp, ebr.F32)
        tag_loss_table = self.datastore['tag_loss_table']
        for t in range(self.T):
            for rlz_losses in tag_loss_table[:, t]:
                for rlz, losses in rlz_losses:
                    losses_by_tag[t, rlz] += losses
        self.datastore['losses_by_tag'] = losses_by_tag
        self.datastore['agg_losses-mean'] = (
            losses_by_tag.sum(axis=0).mean(axis=0))

        self.datastore.create_dset(
            'losses_by_event', h5py.special_dtype(vlen=self.alt_dt),
            (len(self.eids),), fillvalue=None)
        for e in range(len(self.eids)):
            acc = AccumDict(accum=numpy.zeros(self.L * self.I, ebr.F32))
            for rlz_losses in self.datastore['tag_loss_table'][:, e]:
                acc += dict(rlz_losses)  # array of R' items (rlz, losses)
            self.datastore['losses_by_event'][e] = numpy.array(
                sorted(acc.items()), self.alt_dt)
