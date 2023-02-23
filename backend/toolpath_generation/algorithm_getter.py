from .connecting_lines import rect_lines, zigzag_lines
from .horizontal_lines import horizontal_lines
from enum import Enum


class ToolpathAlgorithm(Enum):
    NONE = "none"
    LINES = "lines"
    ZIGZAG = "zigzag"
    RECTLINES = "rectlines"


def get_toolpath_algo(toolpath_algo: ToolpathAlgorithm):
    toolpath_algorithms = {
        ToolpathAlgorithm.NONE: None,
        ToolpathAlgorithm.LINES: horizontal_lines,
        ToolpathAlgorithm.ZIGZAG: zigzag_lines,
        ToolpathAlgorithm.RECTLINES: rect_lines
    }

    if toolpath_algo not in toolpath_algorithms.keys():
        return None

    return toolpath_algorithms[toolpath_algo]
