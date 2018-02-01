# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright (C) 2018 GEM Foundation
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
import getpass
from openquake.baselib import sap
from openquake.commonlib import logs
from openquake.server import views
from openquake.commands import abort


def run(job_ini, prev_id=None):
    """Submit an OpenQuake job and return its ID"""
    job_id, _pid = views.submit_job(job_ini, getpass.getuser(), prev_id)
    return job_id


def status(job_id):
    """Check the status of a job"""
    return logs.dbcmd('calc_info', job_id)


class OQ(object):
    """
    Singleton object with convenience functions which are aliases over
    engine utilities for work in the interactive interpreter.
    """
    def __init__(self):
        from openquake.baselib.datastore import read
        from openquake.commonlib import readinput, calc
        from openquake.calculators.extract import extract
        self.extract = extract
        self.read = read
        self.read_exposure = readinput.Exposure.read
        self.get_oqparam = readinput.get_oqparam
        self.get_site_collection = readinput.get_site_collection
        self.get_exposure = readinput.get_exposure
        self.make_hmap = calc.make_hmap
        self.run = run
        self.status = status
        self.abort = abort.abort
        # TODO: more utilities when be added when deemed useful


@sap.Script
def shell():
    """
    Start an embedded (i)python instance with a global oq object
    """
    oq = OQ()  # noqa
    try:
        import IPython
        IPython.embed(banner1='IPython shell with a global oq object')
    except ImportError:
        import code
        code.interact(banner='Python shell with a global oq object',
                      local=dict(oq=oq))
