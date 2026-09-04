import sys

print("Python:", sys.version)
print("Executable:", sys.executable)

try:
    import torch
    print("PyTorch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
except Exception as exc:
    print("PyTorch import FAILED:", repr(exc))

try:
    import sklearn
    print("scikit-learn:", sklearn.__version__)
    from sklearn.cluster import HDBSCAN
    print("HDBSCAN: available via sklearn.cluster.HDBSCAN")
except Exception as exc:
    print("HDBSCAN import FAILED:", repr(exc))
