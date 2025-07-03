import numpy as np
import matplotlib.pyplot as plt
from matplotlib import use
use('module://backend_ipe')


x = np.linspace(0, 10)
line, = plt.plot(x, np.sin(x), '--', linewidth=2)

dashes = [10, 5, 100, 5]    # 10 points on, 5 off, 100 on, 5 off
line.set_dashes(dashes)


# plt.show()
plt.savefig('line_demo_dash_control.ipe')
