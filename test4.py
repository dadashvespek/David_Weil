import time
from Phidget22.Devices.VoltageRatioInput import VoltageRatioInput
import PythonLibMightyZap_FC as MightyZap
import numpy as np
import matplotlib.pyplot as plt
import math
import pandas as pd
import random

bid = 2  # Actuator ID
top = 600  # Top position
top_initial = 250
bottom = 4000  # Bottom position
initial_current = 800  # Initial current
speed = 100  # Movement speed

# Setup VoltageRatioInput for the force sensor
voltageRatioInput0 = VoltageRatioInput()
voltageRatioInput0.setIsHubPortDevice(True)
voltageRatioInput0.setHubPort(3)
voltageRatioInput0.openWaitForAttachment(5000)
voltageRatioInput0.setDataRate(1000)

# Open MightyZap connection
MightyZap.OpenMightyZap('COM3', 57600)
MightyZap.Restart(bid)
time.sleep(2)
MightyZap.GoalCurrent(bid, 1200)
MightyZap.GoalSpeed(bid, 800)
MightyZap.GoalPosition(bid, top_initial)


def find_base_before_peak(data):
    positions = [point[0] for point in data]
    forces = [point[1] for point in data]
    absolute_changes = [abs(forces[i] - forces[i - 1]) for i in range(1, len(forces))]
    peak_index = np.argmax(absolute_changes)
    base_index = peak_index - 1
    while base_index >= 0 and absolute_changes[base_index] > absolute_changes[peak_index] * 0.1:
        base_index -= 1

    pos1 = positions[base_index]
    force1 = forces[base_index]
    base_index += 1
    pos2 = positions[base_index]
    force2 = forces[base_index]
    mean_pos = (pos1 + 2 * pos2) / 3
    mean_force = (force1 + 2 * force2) / 3
    return mean_pos, mean_force


def move_actuator_down_by_increment_and_read_force(increment, use_high_current=False):
    global bid
    if use_high_current:
        MightyZap.GoalSpeed(bid, 800)
        MightyZap.GoalCurrent(bid, 1200)

    current_position = MightyZap.PresentPosition(bid)
    target_position = max(0, current_position - increment)

    MightyZap.GoalPosition(bid, target_position)

    print(f"Requested to move actuator down by increment {increment} to position: {target_position}")
    time.sleep(0.3)
    while True:
        try:
            actual_position = MightyZap.PresentPosition(bid)
            break
        except:
            pass

    print(f"Actuator moved to position: {actual_position}")
    force = voltageRatioInput0.getSensorValue()
    print(f"Force at position {actual_position}: {force}")

    return actual_position, force


time.sleep(1)


def read_position():
    while True:
        try:
            actual_position = MightyZap.PresentPosition(bid)
            break
        except:
            pass
    return actual_position


def move_actuator_to_position_and_read_force(target_position, use_high_current=False):
    global bid
    if use_high_current:
        MightyZap.GoalSpeed(bid, 800)
        MightyZap.GoalCurrent(bid, 1200)
    if not 0 <= target_position <= 4095:
        print("Error: Target position is out of valid range")
        raise ValueError("Target position is out of valid range")
    MightyZap.GoalPosition(bid, target_position)

    print(f"Requested to move actuator to position: {target_position}")
    time.sleep(0.1)
    while True:
        try:
            actual_position = MightyZap.PresentPosition(bid)
            break
        except:
            pass

    print(f"Actuator moved to position: {actual_position}")
    force = voltageRatioInput0.getSensorValue()
    print(f"Force at position {actual_position}: {force}")

    return actual_position, force


def find_smallest_range_cluster(pos_data):
    sorted_pos_data = sorted(pos_data)
    smallest_range = float('inf')
    smallest_cluster = []
    for i in range(len(sorted_pos_data) - 2):
        cluster = sorted_pos_data[i:i + 3]
        cluster_range = max(cluster) - min(cluster)

        if cluster_range < smallest_range:
            smallest_range = cluster_range
            smallest_cluster = cluster

    return smallest_cluster


def move_actuator_to_top():
    prev_position = -100
    actual_position, force = 0, 0

    while True:
        try:
            actual_position, force = move_actuator_to_position_and_read_force(4000)
            if abs(actual_position - prev_position) <= 10:
                print("Actuator has reached the top.")
                break
            prev_position = actual_position
            print(f"reached position: {actual_position}")

        except ValueError as ve:
            print(f"Encountered a value error: {ve}")
            break

        except Exception as e:
            print(f"Encountered an error: {e}")
            pass

    return actual_position, force


def find_first_significant_point(data):
    positions = [d[0] for d in data]
    forces = [d[1] for d in data]
    force_change = [forces[i] - forces[i - 1] for i in range(1, len(forces))]

    for i in range(1, len(forces) - 1):
        if abs(force_change[i - 1]) > 0.001 and abs(force_change[i]) > 0.001:
            return (positions[i + 2], forces[i + 2])
    return None


def find_thresholds():
    start_position, force = move_actuator_to_top()
    threshold_3 = {"Position": start_position, "Force": force}
    start_position -= 200
    significant_pos = 0
    prev_force = 0
    data = []
    while significant_pos == 0:
        position, force = move_actuator_down_by_increment_and_read_force(20)
        data.append(position)
        if prev_force - force > 0.01 and len(data) > 5:
            significant_pos = position
        prev_force = force
    print(f"SIGNIFICANT FORCE = {significant_pos}")
    range_1 = significant_pos - 40
    range_2 = significant_pos + random.randint(60, 80)
    datas = []
    for _ in range(10):
        move_actuator_to_position_and_read_force(range_2)
        # time.sleep(1)
        while abs(read_position() - range_2) > 13:
            move_actuator_to_position_and_read_force(range_2)
            continue
        data = []
        prev_force = 0
        position = 3000
        while position > range_1:
            position, force = move_actuator_down_by_increment_and_read_force(20)
            data.append((position, force))

            prev_force = force
            # print(data)

        # remove data if force is zero
        data = [point for point in data if point[1] != 0]

        data = data[::-1]
        datas.append(data)
        print(datas)
    final_positions = []
    final_forces = []
    for i, data in enumerate(datas, start=1):
        # Run the function to find threshold_2
        threshold_2_pos, threshold_2_force = find_base_before_peak(data)
        final_positions.append(threshold_2_pos)
        final_forces.append(threshold_2_force)
        threshold_2 = {"Position": threshold_2_pos, "Force": threshold_2_force}
        print(f"Threshold 2 for Dataset {i}: {threshold_2}")

        # Extracting position and force values
        positions = [point[0] for point in data]
        forces = [point[1] for point in data]

        # Calculating absolute change in force between consecutive positions
        absolute_changes = [abs(forces[i] - forces[i - 1]) for i in range(1, len(forces))]

    # Find the smallest range cluster
    print(f"Positions: {final_positions}")
    median_of_positions = np.median(final_positions)
    print(f"Median of Positions: {median_of_positions}")
    smallest_cluster = find_smallest_range_cluster(final_positions)
    print(f"Smallest Range Cluster: {smallest_cluster}")
    # median pos
    median_pos = np.mean(smallest_cluster)
    median_force = np.mean(final_forces)
    threshold_2 = {"Position": median_of_positions, "Force": median_force}
    MightyZap.GoalSpeed(bid, 800)
    MightyZap.GoalCurrent(bid, 800)
    MightyZap.GoalPosition(bid, 800)

    threshold_1_values = []
    data = []
    position = 800
    while True:
        try:
            position_t, force = move_actuator_to_position_and_read_force(position)
            data.append((position, force))
            position += 10
            if force - prev_force > 0.001 and len(data) > 4:
                threshold_1_sample = {'Position': position_t, 'Force': force}
                print(
                    f"Threshold 1 detected at position {threshold_1_sample['Position']} with force {threshold_1_sample['Force']}")
                break
            prev_force = force
        except Exception as e:
            print(f"Error moving actuator to position {position}: {e}")
            continue
    threshold_1_base_pos = threshold_1_sample['Position'] - 35

    for i in range(6):
        MightyZap.GoalPosition(bid, threshold_1_base_pos)
        while abs(read_position() - threshold_1_base_pos) > 15:
            move_actuator_to_position_and_read_force(threshold_1_base_pos)
            continue
        data = []
        prev_force = 0

        for position in range(threshold_1_base_pos, 2500, random.randint(8, 12)):
            try:
                position_t, force = move_actuator_to_position_and_read_force(position)
                data.append((position, force))
                if force - prev_force > 0.001 and len(data) > 1:
                    threshold_1 = {'Position': position_t, 'Force': force}
                    threshold_1_values.append(threshold_1)
                    print(
                        f"Threshold 1 ({i + 1}) detected at position {threshold_1['Position']} with force {threshold_1['Force']}")
                    break
                prev_force = force
            except Exception as e:
                print(f"Error moving actuator to position {position}: {e}")
                continue

    print("All Threshold 1 values:")
    for i, threshold_1 in enumerate(threshold_1_values):
        print(f"Threshold 1 ({i + 1}): {threshold_1}")
    pos_data = [threshold_1["Position"] for threshold_1 in threshold_1_values]

    sorted_pos_data = sorted(pos_data)
    threshold_1 = {"Position": sorted_pos_data[0],
                   "Force": [d['Force'] for d in threshold_1_values if d['Position'] == sorted_pos_data[0]][0]}
    thresholds = [threshold_1, threshold_2, threshold_3]
    print(f"Thresholds: {thresholds}")

    MightyZap.GoalPosition(bid, 800)
    return thresholds


if __name__ == '__main__':
    thresholds = find_thresholds()
    print(thresholds)
    MightyZap.CloseMightyZap()
    voltageRatioInput0.close()
    print("Done")