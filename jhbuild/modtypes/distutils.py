# jhbuild - a build script for GNOME 1.x and 2.x
# Copyright (C) 2001-2006  James Henstridge
#
#   distutils.py: Python distutils module type definitions.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__metaclass__ = type

import os

from jhbuild.errors import BuildStateError
from jhbuild.modtypes import \
     Package, get_dependencies, get_branch, register_module_type

__all__ = [ 'DistutilsModule' ]

class DistutilsModule(Package):
    """Base type for modules that are distributed with a Python
    Distutils style setup.py."""
    type = 'distutils'

    STATE_CHECKOUT = 'checkout'
    STATE_FORCE_CHECKOUT = 'force_checkout'
    STATE_BUILD = 'build'
    STATE_INSTALL = 'install'

    def __init__(self, name, branch,
                 dependencies = [], after = [], suggests = [],
                 supports_non_srcdir_builds = True, extra_env = None):
        Package.__init__(self, name, dependencies, after, suggests, extra_env)
        self.branch = branch
        self.supports_non_srcdir_builds = supports_non_srcdir_builds

    def get_srcdir(self, buildscript):
        return self.branch.srcdir

    def get_builddir(self, buildscript):
        if buildscript.config.buildroot and self.supports_non_srcdir_builds:
            d = buildscript.config.builddir_pattern % (
                os.path.basename(self.get_srcdir(buildscript)))
            return os.path.join(buildscript.config.buildroot, d)
        else:
            return self.get_srcdir(buildscript)

    def get_revision(self):
        return self.branch.tree_id()

    def do_start(self, buildscript):
        pass
    do_start.next_state = STATE_CHECKOUT
    do_start.error_states = []

    def do_checkout(self, buildscript):
        self.checkout(buildscript)
    do_checkout.next_state = STATE_BUILD
    do_checkout.error_states = [STATE_FORCE_CHECKOUT]

    def skip_force_checkout(self, buildscript, last_state):
        return False

    def do_force_checkout(self, buildscript):
        buildscript.set_action(_('Checking out'), self)
        self.branch.force_checkout(buildscript)
    do_force_checkout.next_state = STATE_BUILD
    do_force_checkout.error_states = [STATE_FORCE_CHECKOUT]

    def skip_build(self, buildscript, last_state):
        return buildscript.config.nobuild

    def do_build(self, buildscript):
        buildscript.set_action(_('Building'), self)
        srcdir = self.get_srcdir(buildscript)
        builddir = self.get_builddir(buildscript)
        python = os.environ.get('PYTHON', 'python')
        cmd = [python, 'setup.py', 'build']
        if srcdir != builddir:
            cmd.extend(['--build-base', builddir])
        buildscript.execute(cmd, cwd = srcdir, extra_env = self.extra_env)
    do_build.next_state = STATE_INSTALL
    do_build.error_states = [STATE_FORCE_CHECKOUT]

    def skip_install(self, buildscript, last_state):
        return buildscript.config.nobuild

    def do_install(self, buildscript):
        buildscript.set_action(_('Installing'), self)
        srcdir = self.get_srcdir(buildscript)
        builddir = self.get_builddir(buildscript)
        python = os.environ.get('PYTHON', 'python')
        cmd = [python, 'setup.py']
        if srcdir != builddir:
            cmd.extend(['build', '--build-base', builddir])
        cmd.extend(['install', '--prefix', buildscript.config.prefix])
        buildscript.execute(cmd, cwd = srcdir, extra_env = self.extra_env)
        buildscript.packagedb.add(self.name, self.get_revision() or '')
    do_install.next_state = Package.STATE_DONE
    do_install.error_states = []


def parse_distutils(node, config, uri, repositories, default_repo):
    id = node.getAttribute('id')
    supports_non_srcdir_builds = True

    if node.hasAttribute('supports-non-srcdir-builds'):
        supports_non_srcdir_builds = \
            (node.getAttribute('supports-non-srcdir-builds') != 'no')
    dependencies, after, suggests = get_dependencies(node)
    extra_env = config.module_extra_env.get(id)
    branch = get_branch(node, repositories, default_repo)
    if config.module_checkout_mode.get(id):
        branch.checkout_mode = config.module_checkout_mode[id]

    return DistutilsModule(id, branch,
            dependencies = dependencies, after = after,
            suggests = suggests,
            supports_non_srcdir_builds = supports_non_srcdir_builds,
            extra_env = extra_env)
register_module_type('distutils', parse_distutils)

