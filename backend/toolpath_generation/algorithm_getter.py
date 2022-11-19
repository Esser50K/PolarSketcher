from .connecting_lines import rect_lines, zigzag_lines
from .horizontal_lines import horizontal_lines


def get_toolpath_algo(toolpath_algo: str):
    toolpath_algorithms = {
        "none": None,
        "lines": horizontal_lines,
        "zigzag": zigzag_lines,
        "rectlines": rect_lines
    }

    if toolpath_algo not in toolpath_algorithms.keys():
        return None

    return toolpath_algorithms[toolpath_algo]
