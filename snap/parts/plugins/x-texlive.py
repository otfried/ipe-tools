# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
import os
from subprocess import Popen, PIPE

import snapcraft
from snapcraft.plugins import dump

extras = [ "xcolor", "tcolorbox", "pgf", "ms", "environ", "pgfplots",
           "metalogo", "trimspaces", "etoolbox", "cm-super" ]

class TexLivePlugin(snapcraft.plugins.dump.DumpPlugin):

    def build(self):
        super(dump.DumpPlugin, self).build()

        # Install TexLive with the standard installer
        env = self._build_environment()
        p1 = Popen(['echo', '-n', 'I'], env=env, stdout=PIPE)
        p2 = Popen(['{}/install-tl'.format(self.builddir), '-portable', '-scheme', 'basic'], env=env, stdin=p1.stdout, stdout=PIPE)
        output = p2.communicate()[0]
        self.run(['{}/texlive/bin/x86_64-linux/tlmgr'.format(self.installdir),
                  'install'] + extras, env=env)

    def _build_environment(self):
        env = os.environ.copy()
        env['TEXLIVE_INSTALL_PREFIX'] = os.path.join(self.installdir, 'texlive')
        return env
