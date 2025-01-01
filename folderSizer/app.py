import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import Tk, filedialog
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent


def get_total_folder_size(path):
    total_size = 0
    try:
        for item in path.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
    except (PermissionError, FileNotFoundError):
        print(f"Skipping inaccessible folder: {path}")
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
    history = [path]

    def perform_analysis(directory):
        nonlocal folder_sizes, files_sizes

        folder_sizes.clear()
        files_sizes.clear()

        print(f"\nAnalyzing folder sizes in {directory}...\n")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(analyze_folder, subfolder): subfolder
                for subfolder in directory.iterdir() if subfolder.is_dir()
            }

            for future in as_completed(futures):
                subfolder, file_size, total_size = future.result()
                folder_sizes[subfolder] = total_size
                files_sizes[subfolder] = file_size
                print(f"{subfolder.name} - Total: {format_size(total_size)} | Files: {format_size(file_size)}")

        plot_folder_sizes(folder_sizes, files_sizes, directory, perform_analysis, history)

    perform_analysis(path)


def plot_folder_sizes(folder_sizes, files_sizes, target_dir, callback, history):
    subfolders = list(folder_sizes.keys())
    total_sizes = list(folder_sizes.values())
    file_sizes = list(files_sizes.values())

    fig, ax = plt.subplots(figsize=(12, 7))
    bar_width = 0.4
    x_pos = range(len(subfolders))

    bars_total = ax.bar(x_pos, total_sizes, width=bar_width, label='Total Size', color='dodgerblue')
    ax.bar(x_pos, file_sizes, width=bar_width * 0.7, label='File Size (Root)', color='orange')

    plt.xlabel("Subfolders")
    plt.ylabel("Size (Bytes)")
    plt.title(f"Folder Size Analysis - {target_dir}")
    plt.xticks(x_pos, [sf.name for sf in subfolders], rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()

    # Tooltip for size display
    annot = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round", fc="w"),
                        arrowprops=dict(arrowstyle="->"))
    annot.set_visible(False)

    def update_tooltip(event: MouseEvent):
        vis = annot.get_visible()
        for i, bar in enumerate(bars_total):
            if bar.contains(event)[0]:
                x = bar.get_x() + bar.get_width() / 2
                y = bar.get_height()
                annot.xy = (x, y)
                folder_name = subfolders[i].name
                size_text = format_size(total_sizes[i])
                annot.set_text(f"{folder_name}\n{size_text}")
                annot.set_visible(True)
                fig.canvas.draw_idle()
                return
        if vis:
            annot.set_visible(False)
            fig.canvas.draw_idle()

    def on_click(event: MouseEvent):
        for i, bar in enumerate(bars_total):
            if bar.contains(event)[0]:
                subfolder_path = subfolders[i]
                print(f"\nDrilling down into: {subfolder_path}...\n")
                plt.close(fig)
                history.append(subfolder_path)
                callback(subfolder_path)

    def on_right_click(event: MouseEvent):
        if event.button == 3 and len(history) > 1:  # Right-click to go back
            history.pop()  # Remove current path from history
            parent_dir = history[-1]
            print(f"\nReturning to: {parent_dir}...\n")
            plt.close(fig)
            callback(parent_dir)

    fig.canvas.mpl_connect("motion_notify_event", update_tooltip)
    fig.canvas.mpl_connect("button_press_event", on_click)
    fig.canvas.mpl_connect("button_press_event", on_right_click)

    plt.show()


def pick_folder():
    Tk().withdraw()
    return filedialog.askdirectory(title="Select Folder to Analyze")


if __name__ == "__main__":
    while True:
        target_dir = pick_folder()

        if not target_dir:
            print("No folder selected. Exiting...")
            break
        
        analyze_and_plot(target_dir)
