"""Entraîne une version (SimpleCNN ou ResNet18) sur figshare et exporte ses prédictions de test.

Suit PROTOCOL.md : séparation par patient issue de figshare_eval/manifest.csv, checkpoint
de meilleure macro-F1 de validation, test utilisé une seule fois à la fin.

    python experiments/brain_mri/train.py simplecnn
    python experiments/brain_mri/train.py resnet18
"""

import os

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")  # requis pour le déterminisme CUDA

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import random  # noqa: E402
import subprocess  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
import torch.nn.functional as F  # noqa: E402
import torchvision  # noqa: E402
from PIL import Image  # noqa: E402
from torchvision.transforms import v2  # noqa: E402

from medvision_qa.classes import ClassSpec  # noqa: E402
from medvision_qa.metrics import compute_metrics  # noqa: E402

SEED = 20261029
CLASSES = ClassSpec(("glioma", "meningioma", "pituitary"), ("glioma",))
SIZE = 224
BATCH = 32
MAX_EPOCHS = 15
LR = {"simplecnn": 1e-3, "resnet18": 1e-4}
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "figshare"
EVAL_DIR = HERE / "figshare_eval"
MODELS_DIR = ROOT / "data" / "models"


class SimpleCNN(nn.Module):
    """Architecture reprise de MousJB/brain-tumor-mri-classification (src/models.py, MIT)."""

    def __init__(self, num_classes):
        super().__init__()
        self.conv1, self.bn1 = nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32)
        self.conv2, self.bn2 = nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64)
        self.conv3, self.bn3 = nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128)
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.5)
        self.fc1 = nn.Linear(128 * 28 * 28, 256)
        self.fc2 = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        x = self.dropout(F.relu(self.fc1(x.flatten(1))))
        return self.fc2(x)


def build_model(name):
    if name == "simplecnn":
        return SimpleCNN(len(CLASSES.order))
    model = torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.IMAGENET1K_V1)
    model.fc = nn.Linear(model.fc.in_features, len(CLASSES.order))
    return model


def normalise(name, x):
    """x : (N, 1, H, W) dans [0, 1]."""
    if name == "simplecnn":
        return (x - 0.5) / 0.5
    mean = torch.tensor([0.485, 0.456, 0.406], device=x.device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=x.device).view(1, 3, 1, 1)
    return (x.repeat(1, 3, 1, 1) - mean) / std


def load_split():
    index = json.loads((DATA / "png_index.json").read_text(encoding="utf-8"))
    with (EVAL_DIR / "manifest.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_split = {}
    for r in rows:
        by_split.setdefault(r["split"], []).append(r)
    tensors = {}
    for name in ("train", "val", "test"):
        items = sorted(by_split[name], key=lambda r: r["case_id"])
        images = np.stack([np.asarray(Image.open(DATA / index[r["case_id"]]).convert("L")
                                      .resize((SIZE, SIZE), Image.Resampling.BILINEAR)) for r in items])
        labels = np.array([CLASSES.index[r["label"]] for r in items])
        tensors[name] = (torch.from_numpy(images).unsqueeze(1), torch.from_numpy(labels),
                         [r["case_id"] for r in items])
    return tensors


def predict(model, name, images, device):
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(images), 64):
            x = normalise(name, images[i:i + 64].to(device).float() / 255)
            out.append(torch.softmax(model(x).double(), dim=1).cpu())
    return torch.cat(out).numpy()


def macro_f1(y, probs):
    return compute_metrics(CLASSES, y, probs.argmax(axis=1), probs)["macro_f1"]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=("simplecnn", "resnet18"))
    args = parser.parse_args()
    name = args.model

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    data = load_split()
    x_train, y_train, _ = data["train"]
    model = build_model(name).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR[name])
    augment = v2.Compose([v2.RandomHorizontalFlip(), v2.RandomRotation(10)])
    generator = torch.Generator().manual_seed(SEED)

    history, best = [], None
    start = time.time()
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        order = torch.randperm(len(x_train), generator=generator)
        total = 0.0
        for i in range(0, len(order), BATCH):
            idx = order[i:i + BATCH]
            x = augment(x_train[idx].to(device)).float() / 255
            loss = F.cross_entropy(model(normalise(name, x)), y_train[idx].to(device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        val = macro_f1(data["val"][1].numpy(), predict(model, name, data["val"][0], device))
        history.append({"epoch": epoch, "train_loss": total / len(order),
                        "val_macro_f1": val.value, "val_macro_f1_undefined": val.undefined_reason})
        print(f"[{name}] époque {epoch:2d}  perte {total / len(order):.4f}  macro-F1 val {val.value}", flush=True)
        if val.defined and (best is None or val.value > best[1]):
            best = (epoch, val.value, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()})

    model.load_state_dict(best[2])
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    weights_path = MODELS_DIR / f"{name}_figshare_v1.pt"
    torch.save(best[2], weights_path)
    weights_sha256 = hashlib.sha256(weights_path.read_bytes()).hexdigest()

    x_test, y_test, test_ids = data["test"]
    probs = np.round(predict(model, name, x_test, device), 6)
    with (EVAL_DIR / f"preds_{name}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["case_id", "predicted_label"] + list(CLASSES.score_columns))
        for case_id, p in zip(test_ids, probs):
            writer.writerow([case_id, CLASSES.order[int(np.argmax(p))]] + [f"{v:.6f}" for v in p])

    record = {
        "model": name, "seed": SEED, "image_size": SIZE, "batch_size": BATCH, "max_epochs": MAX_EPOCHS,
        "learning_rate": LR[name], "optimizer": "Adam", "augmentation": "RandomHorizontalFlip, RandomRotation(10), paramètres tirés une fois par lot",
        "selection": "meilleure macro-F1 de validation", "best_epoch": best[0], "best_val_macro_f1": best[1],
        "history": history, "n_train": len(x_train), "n_val": len(data["val"][0]), "n_test": len(x_test),
        "weights_file": weights_path.name, "weights_sha256": weights_sha256, "code_commit": git_commit(),
        "duration_s": round(time.time() - start, 1), "device": torch.cuda.get_device_name(0) if device.type == "cuda" else "cpu",
        "python": platform.python_version(), "torch": torch.__version__, "torchvision": torchvision.__version__,
        "cuda": torch.version.cuda,
        "determinism": "partiel : graines fixées et algorithmes déterministes demandés (warn_only) ; certaines opérations CUDA (rétropropagation du pooling) n'ont pas de version déterministe",
    }
    (EVAL_DIR / f"training_{name}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                                                   encoding="utf-8", newline="\n")
    print(f"[{name}] meilleure époque {best[0]} (macro-F1 val {best[1]:.4f}), poids {weights_sha256[:12]}…")


if __name__ == "__main__":
    main()
