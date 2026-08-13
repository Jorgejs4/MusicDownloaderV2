import os
import sys


def _set_tk_env():
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return

    tcl_root = os.path.join(base, "tcl")
    tcl_lib = os.path.join(tcl_root, "tcl8.6")
    tk_lib = os.path.join(tcl_root, "tk8.6")

    if os.path.isdir(tcl_lib):
        os.environ["TCL_LIBRARY"] = tcl_lib
    if os.path.isdir(tk_lib):
        os.environ["TK_LIBRARY"] = tk_lib


_set_tk_env()
