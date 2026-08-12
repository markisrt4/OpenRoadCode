# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import sys

sys.path.append("../network")

from GqrxCtrl import GqrxCtrl

# Argv[1] is ip address
ip_addr = sys.argv[1]

# Setup GQRX
gqrx = GqrxCtrl(ip_addr, True)

gqrx.gqrxSetDemodMode("WFM_ST")
gqrx.gqrxTuneFreq(97100000)
