"""Train the ideal crossbar on the shared task, and record what it scores.

Minimal by policy. The model is one crossbar -- 36 inputs, 10 columns -- and the
whole of the learning is softmax cross-entropy on its column currents. The
complexity of this project belongs in the device physics and the error model, and
a better classifier here would buy nothing: the ideal accuracy is a **baseline the
tolerance study is measured against**, not a result.

That is also the answer to whether this repo needs PyTorch. The gradient of
softmax cross-entropy through a linear map is ``X.T @ (p - Y)``. Autograd for one
line of calculus is not worth the largest dependency in the project, so ``torch``
was removed from ``pyproject.toml`` rather than installed.

Two things here are physics rather than machine learning:

**The window constrains the weight pattern's shape, not its scale.** Training is
unconstrained, and the result is divided by ``max|w|`` at the end so every weight
lands inside ``[-1, 1]``. That rescaling is free: a positive global factor on the
column currents cannot change an argmax, and the factor is carried as a readout
gain so the logits remain reconstructible. photonn does exactly this on the other
side of the series -- its handoff records ``sigma`` passivized to <= 1 with an
external gain of 3.9068, logit-preserving.

The first version of this file projected onto ``[-1, 1]`` after every step
instead, which sounds more physical and is not. It clips inside the descent, so it
distorts the direction rather than the reachable set, and it cost **5.7 points of
accuracy** (0.6775 against 0.7345) while parking 27% of the weights on the window
edge. The window was not binding; the optimiser was. Note the gain amplifies noise
along with signal, so it buys no signal-to-noise -- it only removes a constraint
that was never physical.

**There is no bias.** A crossbar column sums the currents on its wire and nothing
else. A bias would be an extra row of devices driven at a fixed voltage; that is a
real design option, and it is not taken here because it is device count spent
outside the thing being measured.

Run (from the repo root, in this repo's venv)::

    .venv/Scripts/python.exe -m apps.train_crossbar
    .venv/Scripts/python.exe -m apps.train_crossbar --quick
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from spinn.crossbar import Crossbar, accuracy
from spinn.export import SIGNED_SCHEMES, validate_handoff, write_handoff
from spinn.task import N_CLASSES, load_shared_task, one_hot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(REPO, "exports")

#: Fixed and recorded, per project convention.
SEED = 20260908


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def cross_entropy(probs: np.ndarray, targets: np.ndarray) -> float:
    return float(-np.mean(np.sum(targets * np.log(probs + 1e-12), axis=1)))


def train(inputs, targets, *, epochs, lr, batch, seed):
    """Minibatch gradient descent on the crossbar's weight matrix.

    ``inputs`` are the normalised row voltages divided by the read voltage, which
    is exactly what an ideal crossbar's decode returns a matrix product against --
    so the linear map trained here *is* the array, not a stand-in for it.

    Unconstrained. The conductance window is imposed afterwards by
    :func:`fit_to_window`, because it bounds the pattern's shape and not its scale.
    """
    rng = np.random.default_rng(seed)
    n, n_in = inputs.shape
    # Small symmetric start. A crossbar has no notion of a preferred sign, so there
    # is nothing to gain from a wide or asymmetric initialisation.
    weights = rng.uniform(-0.05, 0.05, size=(n_in, targets.shape[1]))

    for epoch in range(epochs):
        order = rng.permutation(n)
        for start in range(0, n, batch):
            idx = order[start:start + batch]
            x, y = inputs[idx], targets[idx]
            probs = softmax(x @ weights)
            weights -= lr * (x.T @ (probs - y)) / len(idx)
        loss = cross_entropy(softmax(inputs @ weights), targets)
        yield epoch, loss, weights


def fit_to_window(weights: np.ndarray) -> tuple[np.ndarray, float]:
    """Scale weights into ``[-1, 1]``; return them and the gain that undoes it.

    ``readout_gain`` is what a downstream stage must apply to recover the trained
    logits, and it has to cross the handoff: without it MATLAB reconstructs
    correctly-classified but wrongly-scaled logits, which is invisible in an
    accuracy and wrong in anything derived from a margin.
    """
    gain = float(np.abs(weights).max())
    if gain == 0.0:
        raise ValueError("weights are all zero; nothing was learned")
    return weights / gain, gain


def parse_args():
    p = argparse.ArgumentParser(description="Train an ideal spintronic crossbar.")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--lr", type=float, default=0.5)
    p.add_argument("--batch", type=int, default=128)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--scheme", default="differential", choices=("differential", "offset"))
    p.add_argument("--quick", action="store_true", help="fast smoke config")
    return p.parse_args()


def main():
    args = parse_args()
    if args.quick:
        args.epochs = 5

    task = load_shared_task()
    cb = Crossbar(task.n_channels, N_CLASSES, scheme=args.scheme)

    # The array's own encoding, used for training as well as evaluation, so there
    # is one preprocessing path rather than two that can drift.
    x_train = cb.encode(task.train_images) / cb.read_voltage
    x_test = cb.encode(task.test_images) / cb.read_voltage
    y_train = one_hot(task.train_labels, N_CLASSES)

    print(f"crossbar   {cb.n_inputs}x{cb.n_outputs}, {args.scheme}, "
          f"{cb.n_devices} devices, window ratio {cb.ratio:g}")
    print(f"task       train {task.train_images.shape}, test {task.test_images.shape}")

    raw = None
    for epoch, loss, raw in train(
        x_train, y_train, epochs=args.epochs, lr=args.lr, batch=args.batch,
        seed=args.seed,
    ):
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            acc = accuracy(x_test @ raw, task.test_labels)
            print(f"  epoch {epoch:3d}  loss {loss:.4f}  test acc {acc:.4f}")

    weights, gain = fit_to_window(raw)
    assert accuracy(x_test @ weights, task.test_labels) == accuracy(
        x_test @ raw, task.test_labels
    ), "rescaling into the window changed a prediction; it must not"

    # Evaluate through the array itself, not the shortcut the training loop used.
    # If these disagree, the decode is wrong and every number after it is too.
    logits = cb.forward(task.test_images, weights)
    ideal = accuracy(logits, task.test_labels)
    assert np.allclose(logits, x_test @ weights), "the array and the linear map disagree"

    train_acc = accuracy(x_train @ weights, task.train_labels)
    print(f"\nideal accuracy  {ideal:.4f}  (train {train_acc:.4f})")
    print(f"readout gain    {gain:.4f}  (logit-preserving; argmax is scale-invariant)")
    print(f"weights         [{weights.min():+.3f}, {weights.max():+.3f}], "
          f"{np.mean(np.abs(weights) > 0.999):.1%} at the window edge")

    os.makedirs(EXPORTS, exist_ok=True)
    out = os.path.join(EXPORTS, "crossbar_ideal.npz")
    np.savez_compressed(
        out, weights=weights, readout_gain=gain, seed=args.seed, scheme=args.scheme,
        ideal_accuracy=ideal, epochs=args.epochs, lr=args.lr, batch=args.batch,
    )
    print(f"wrote {out}")

    handoff = os.path.join(EXPORTS, "crossbar_handoff.h5")
    write_handoff(
        handoff,
        model_type="crossbar",
        parameters={"weights": weights},
        geometry={
            "n_rows": cb.n_inputs,
            "n_cols": cb.n_outputs,
            "devices_per_weight": cb.devices_per_weight,
        },
        operating_point={
            "g_min_s": cb.g_min,
            "g_max_s": cb.g_max,
            "read_voltage_v": cb.read_voltage,
            "readout_gain": gain,
            "signed_scheme_code": SIGNED_SCHEMES[cb.scheme],
        },
        test_images=task.test_images,
        test_labels=task.test_labels,
        description=(
            f"spintronic crossbar | {cb.n_inputs}x{cb.n_outputs} {args.scheme} | "
            f"{cb.n_devices} devices | ideal_acc={ideal:.4f} | seed={args.seed} | "
            f"weights index [g_min_s, g_max_s]; readout_gain restores the logit scale"
        ),
        test_acc=ideal,
    )
    validate_handoff(handoff)
    print(f"wrote {handoff} (validated)")


if __name__ == "__main__":
    main()
