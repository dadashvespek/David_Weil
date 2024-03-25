data =[(2642, 0), (2622, 0.13501), (2603, 0.10477), (2581, 0.10287), (2564, 0.09927), (2548, 0.09735), (2532, 0.09567), (2516, 0.09467), (2499, 0.09384), (2488, 0.09283), (2469, 0.09265), (2450, 0.09238), (2437, 0.0903), (2416, 0.08981), (2401, 0.08923), (2381, 0.08826), (2359, 0.08765), (2348, 0.08633), (2328, 0.08459), (2311, 0.06653), (2294, 0.01703), (2275, 0.00952), (2259, 0.00952), (2243, 0.00925), (2221, 0.009), (2204, 0.00861), (2194, 0.00882), (2178, 0.00885), (2161, 0.00854), (2142, 0.00809), (2128, 0.00793), (2118, 0.00784), (2096, 0.00803), (2080, 0.0083), (2065, 0.00803), (2045, 0.00754), (2030, 0.00748), (2015, 0.00702), (2006, 0.00726), (1994, 0.0087), (1982, 0.00742), (1965, 0.00742), (1948, 0.0076), (1933, 0.00742), (1916, 0.00748), (1900, 0.00748), (1883, 0.00763), (1867, 0.00754), (1850, 0.00735), (1834, 0.00696), (1818, 0.00699), (1801, 0.00717), (1784, 0.00696), (1769, 0.00745), (1757, 0.00732), (1746, 0.00775), (1728, 0.00742), (1713, 0.0079), (1698, 0.00781), (1685, 0.00818), (1666, 0.00769), (1650, 0.00708), (1638, 0.00647), (1623, 0.00665), (1605, 0.0069), (1589, 0.00647), (1572, 0.00665), (1556, 0.00677), (1541, 0.00623), (1521, 0.00616), (1507, 0.00696), (1491, 0.00662), (1474, 0.00592), (1457, 0.00568), (1442, 0.00543), (1425, 0.00546), (1409, 0.00571), (1390, 0.00562), (1376, 0.00516), (1355, 0.00516), (1341, 0.00516), (1327, 0.00531), (1307, 0.00534), (1287, 0.00528), (1272, 0.00528), (1253, 0.0051), (1240, 0.00491), (1224, 0.00497), (1212, 0.00497), (1197, 0.00519), (1181, 0.00525), (1164, 0.00525), (1147, 0.00568), (1133, 0.00562), (1115, 0.00558), (1103, 0.00558), (1088, 0.00537), (1073, 0.00504), (1060, 0.00516), (1048, 0.0047), (1034, 0.00461), (1017, 9e-05), (1005, 6e-05), (993, 0.0), (981, 0.00027), (968, 0.00021), (951, 0.00015), (936, 9e-05), (926, 0.0), (917, 3e-05), (903, 0.00027), (892, 0.00024), (880, 0.00018), (864, 3e-05), (852, 0.0), (836, 9e-05), (824, 0.00027), (814, 0.00021), (804, 0.00012), (789, 0.00012)]
data = data[::-1]
data = data[:-1]
import matplotlib.pyplot as plt
import numpy as np
positions = [point[0] for point in data]
forces = [point[1] for point in data]

# Calculating absolute change in force between consecutive positions
absolute_changes = [abs(forces[i] - forces[i-1]) for i in range(1, len(forces))]

# Find index of the peak
peak_index = np.argmax(absolute_changes)

# Find the base before the peak
base_index = peak_index - 1
while base_index >= 0 and absolute_changes[base_index] > absolute_changes[peak_index] * 0.1:
    base_index -= 1

# Print the position and absolute change values of the base before the peak
print("Base before the peak:")
print("Position:", positions[base_index])
print("Absolute Change in Force:", absolute_changes[base_index])

# Plotting absolute change graph
plt.plot(positions[1:], absolute_changes, marker='o', linestyle='-', color='b', markersize=5)
plt.xlabel('Position')
plt.ylabel('Absolute Change in Force')
plt.title('Absolute Change in Force vs. Position')

# Marking the base before the peak
plt.scatter(positions[base_index + 1], absolute_changes[base_index], color='green', label='Base before peak')
plt.annotate(f'({positions[base_index]}, {absolute_changes[base_index]:.6f})',
             xy=(positions[base_index + 1], absolute_changes[base_index]),
             xytext=(positions[base_index + 1] + 10, absolute_changes[base_index] + 0.0005),
             arrowprops=dict(facecolor='black', arrowstyle='->'),
             )

plt.grid(True)
plt.legend()
plt.show()