import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import Tk, filedialog, Button
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent


def get_total_folder_size(path, max_depth=1):
    total_size = 0
    start_time = time.time()

    try:
        for item in path.iterdir():
            if item.is_file():
                total_size += item.stat().st_size
            elif item.is_dir():
                total_size += analyze_subfolder(item, max_depth)
    except (PermissionError, FileNotFoundError):
        print(f"Skipping inaccessible folder: {path}")

    elapsed_time = time.time() - start_time
    if elapsed_time > 3:
        print(f"Splitting analysis for: {path}")
        total_size = split_analysis(path, max_depth + 1)

    return total_size


def analyze_subfolder(folder, max_depth=1):
    total_size = 0
    try:
        for item in folder.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
    except (PermissionError, FileNotFoundError):
        print(f"Skipping inaccessible folder: {folder}")
    return total_size


def split_analysis(path, max_depth):
    total_size = 0
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(analyze_subfolder, subfolder, max_depth)
                   for subfolder in path.iterdir() if subfolder.is_dir()]

        for future in as_completed(futures):
            total_size += future.result()

    return total_size


def analyze_folder(path):
    total_size = 0
    files_size = 0
    try:
        files_size = sum(item.stat().st_size for item in path.iterdir() if item.is_file())
        subfolder_size = get_total_folder_size(path)
        total_size = subfolder_size
    except (PermissionError, FileNotFoundError):
        print(f"Skipping inaccessible folder: {path}")

    return path, files_size, total_size


def analyze_files_in_directory(path):
    files_info = {}
    try:
        for file in path.iterdir():
            if file.is_file():
                files_info[file] = file.stat().st_size
    except (PermissionError, FileNotFoundError):
        print(f"Skipping inaccessible file: {file}")
    return files_info


def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1048576:
        return f"{size // 1024} KB"
    elif size < 1073741824:
        return f"{size // 1048576} MB"
    else:
        return f"{size // 1073741824} GB"


def analyze_and_plot(target_dir, max_workers=8):
    path = Path(target_dir)
    if not path.exists() or not path.is_dir():
        print("Directory does not exist.")
        return

    folder_sizes = {}
    files_sizes = {}
    files_info = {}
    history = [path]

    def perform_analysis(directory):
        nonlocal folder_sizes, files_sizes, files_info

        folder_sizes.clear()
        files_sizes.clear()
        files_info.clear()

        print(f"\nAnalyzing folder sizes in {directory}...\n")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_folder, subfolder): subfolder
                       for subfolder in directory.iterdir() if subfolder.is_dir()}

            files_info = analyze_files_in_directory(directory)

            for future in as_completed(futures):
                subfolder, file_size, total_size = future.result()
                folder_sizes[subfolder] = total_size
                files_sizes[subfolder] = file_size
                print(f"{subfolder.name} - Total: {format_size(total_size)} | Files: {format_size(file_size)}")

        plot_folder_sizes(folder_sizes, files_sizes, files_info, directory, perform_analysis, history)

    perform_analysis(path)


def plot_folder_sizes(folder_sizes, files_sizes, files_info, target_dir, callback, history):
    subfolders = list(folder_sizes.keys())
    total_sizes = list(folder_sizes.values())
    file_sizes = list(files_sizes.values())

    file_names = list(files_info.keys())
    file_values = list(files_info.values())

    total_dir_size = sum(total_sizes) + sum(file_values)

    fig, ax = plt.subplots(figsize=(12, 8))
    bar_width = 0.4
    x_pos = range(len(subfolders) + len(file_names))

    bars_total = ax.bar(x_pos[:len(subfolders)], total_sizes, width=bar_width, label='Folders', color='dodgerblue')
    bars_files = ax.bar(x_pos[len(subfolders):], file_values, width=bar_width, label='Files', color='green')

    plt.xticks(
        x_pos,
        [sf.name for sf in subfolders] + [f.name for f in file_names],
        rotation=45,
        ha="right"
    )
    plt.tight_layout()

    annot = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                        textcoords="offset points", bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_tooltip(event):
        vis = annot.get_visible()
        for i, bar in enumerate(bars_total + bars_files):
            if bar.contains(event)[0]:
                x = bar.get_x() + bar.get_width() / 2
                y = bar.get_height()
                annot.xy = (x, y)
                if i < len(subfolders):
                    label = subfolders[i].name
                    size = total_sizes[i]
                else:
                    label = file_names[i - len(subfolders)].name
                    size = file_values[i - len(subfolders)]
                    percentage = (size / total_dir_size) * 100
                    label += f" - {format_size(size)} | {percentage:.2f}% of total"
                annot.set_text(label)
                annot.set_visible(True)
                fig.canvas.draw_idle()
                return
        if vis:
            annot.set_visible(False)
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", update_tooltip)

    def go_back():
        if len(history) > 1:
            history.pop()
            plt.close(fig)
            callback(history[-1])

    back_button = Button(plt.gcf().canvas.get_tk_widget(), text="..", command=go_back)
    back_button.place(x=10, y=10)

    plt.show()


if __name__ == "__main__":
    while True:
        target_dir = filedialog.askdirectory(title="Select Folder to Analyze")
        if not target_dir:
            print("No folder selected. Exiting...")
            break
        analyze_and_plot(target_dir)
