import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("top_5000_locations.csv")

plt.scatter(df.longitude, df.latitude, alpha=0.2, c='b', s=10)
plt.xlim(-126, -66)
plt.ylim(23, 50)

plt.show()
