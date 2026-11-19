"""
common_util.py

Utils shared by the ONNX runtime users.

"""

import onnxruntime as ort

def make_session(model_path, providers=None):
    """
    Create an ort.InferenceSession with the CPU memory arena disabled.

    By default, ort.InferenceSession uses enable_cpu_mem_arena=True, which
    causes the ONNX Runtime allocator to retain the peak allocation across
    all calls and never release it back to the OS.  When a long-lived process
    processes many PDFs that differ in page size or element count, the arena
    grows without bound and is never reclaimed even after gc.collect().

    Setting enable_cpu_mem_arena=False makes the runtime release allocations
    promptly, keeping RSS stable across documents.
    """
    so = ort.SessionOptions()
    so.enable_cpu_mem_arena = False
    return ort.InferenceSession(model_path, sess_options=so, providers=providers)
