"""ComfyUI 自定义节点入口。

把整个目录放到 ComfyUI/custom_nodes/ 下，重启后
在节点面板的 sampling/krea2 分类里能找到「Krea2 多尺度采样器」。
"""

from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
