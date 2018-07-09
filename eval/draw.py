import numpy as np
import matplotlib.pyplot as plt
import matplotlib
font = {'family' : 'serif',
        'weight' : 'normal',
        'size'   : 28,
        }
matplotlib.rc('font', **font)

l1=(0.5, 0.7729, 0.7698, 0.7341, 0.771)
lx=(0.125, 0.25, 0.5, 0.75, 1)

l2=(0.45, 0.7005, 0.7053, 0.6961, 0.7041)

line1= plt.plot(lx, l1, ':k8',label='Small',linewidth=2)
line2= plt.plot(lx, l2, '-k8',label='Large',linewidth=2)

plt.xlim(0,1.02)

plt.ylim(0.2,0.9)
plt.ylabel('Accuracy')
plt.xlabel('Size')

plt.tight_layout()
plt.legend(loc='lower right')
plt.show()