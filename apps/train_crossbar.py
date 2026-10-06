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

**The grid.** ``--grid g`` trains a ``g*g`` by 10 array on the same 2,000 test digits
at that resolution, for the array-size sweep (``docs/array_size.md``). Only 6 is the
shared task the comparison table rests on. The learning rate scales as
``0.5 * 36 / rows``: the step of a softmax regression goes with ``||x||^2``, which grows
with the pixel count, so an unscaled 0.5 at 676 inputs oscillates and the "ideal"
accuracy would be the optimiser's artefact -- the mistake the projected-descent
version above already made once. At 6x6 it is exactly 0.5, so that array is unchanged.

**The window ratio.** ``--ratio r`` writes the same array with ``g_max = r * g_min``,
holding ``g_min`` at the design's 1 uS, into ``exports/ratio/``. The design's ratio
is 3; the two integrated three-terminal devices imec measured come in at 2.03 and
1.85 (``docs/history.md``, 2026-10-04), and the delivered spread is judged at all
three. Training never sees the window, so the weights are identical and only the
handoff's operating point differs. These are a sensitivity, not designs.

**The calibrated scale.** ``--calibrate-states S`` writes the row's own weights with full
scale at ``c * max|w|`` instead of ``max|w|``, into ``exports/scale/s<S>/``. Like the
window, the scale is a programming choice and not training: the window bounds the
pattern's shape, so where the largest weight sits in it is free. Mapping ``max|w|`` to
full scale lets one outlier set the lattice for all 720 devices, and at five levels per
device that rounds about half the weights to zero. ``c`` is chosen on the **train** set,
by :func:`calibrate_scale`, and the larger weights are clipped. The handoff carries
``clip(w / c, -1, 1)`` and the readout gain times ``c``, so ``program()`` at S states
performs the calibrated quantisation and nothing downstream changes. **The row itself
keeps ``max|w|``**; this is a sensitivity, like ``--ratio``, and covers 36x10 only.

Run (from the repo root, in this repo's venv)::

    .venv/Scripts/python.exe -m apps.train_crossbar
    .venv/Scripts/python.exe -m apps.train_crossbar --quick
    .venv/Scripts/python.exe -m apps.train_crossbar --grid 12
    .venv/Scripts/python.exe -m apps.train_crossbar --ratio 2.03
    .venv/Scripts/python.exe -m apps.train_crossbar --calibrate-states 5
"""
from __future__ import annotations

import argparse
import os

import numpy as np

from spinn.crossbar import G_MIN, Crossbar, accuracy
from spinn.export import SIGNED_SCHEMES, validate_handoff, write_handoff
from spinn.task import N_CHANNELS, N_CLASSES, ROW_GRID, load_shared_task, one_hot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(REPO, "exports")

#: Fixed and recorded, per project convention.
SEED = 20260908

#: The learning rate at the row's 36 inputs; see the module docstring for the scaling.
BASE_LR = 0.5


def learning_rate(rows: int) -> float:
    """``0.5 * 36 / rows``: constant step in ``||x||^2``. Exactly ``0.5`` at 36 rows."""
    return BASE_LR * N_CHANNELS / rows


def output_dir(grid: int) -> str:
    """Where a grid's handoff lands: the row's own in ``exports/``, the rest under it."""
    if grid == ROW_GRID:
        return EXPORTS
    return os.path.join(EXPORTS, "size", f"g{grid:02d}")


def ratio_dir(ratio: float) -> str:
    """Where a window-ratio variant lands: ``exports/ratio/r2p03`` for 2.03."""
    return os.path.join(EXPORTS, "ratio", "r" + f"{ratio:.2f}".replace(".", "p"))


def ratio_crossbar(n_inputs: int, n_outputs: int, ratio: float | None, **kw) -> Crossbar:
    """The design's crossbar, or with ``g_max = ratio * g_min`` and ``g_min`` held.

    Holding the off state keeps the state most devices sit in -- a zero weight is two
    devices off -- at the design's 1 MOhm. Under a multiplicative spread only the
    ratio reaches the accuracy, so the choice of which end to hold matters only to IR
    drop and power, which the variants are not run for.
    """
    if ratio is None:
        return Crossbar(n_inputs, n_outputs, **kw)
    return Crossbar(n_inputs, n_outputs, g_min=G_MIN, g_max=ratio * G_MIN, **kw)


def scale_dir(states: int) -> str:
    """Where a calibrated-scale variant lands: ``exports/scale/s5`` for five states."""
    return os.path.join(EXPORTS, "scale", f"s{states}")


#: ``c = k / 20`` for ``k = 6 ... 20``: 0.30, 0.35, ..., 1.00. Built from integers so
#: each candidate is the correctly rounded quotient, with no accumulated step.
SCALE_CANDIDATES = tuple(k / 20 for k in range(6, 21))


def scale_to_window(weights: np.ndarray, c: float) -> np.ndarray:
    """Full scale at ``c * max|w|``: ``clip(w / (c * max|w|), -1, 1)``.

    ``c = 1`` is the row's own :func:`fit_to_window`. Below 1 the lattice is finer for
    the bulk of the weights and the few above ``c * max|w|`` are clipped to the rails.
    """
    return np.clip(weights / (c * np.abs(weights).max()), -1.0, 1.0)


def calibrate_scale(weights, x_train, train_labels, states, *, scheme="differential") -> float:
    """The ``c`` that gives the best **train**-set accuracy at ``states`` levels per device.

    This is a programming choice and not training: the window bounds the weight
    pattern's shape, not its scale, so where ``max|w|`` lands in it is free. Mapping it
    to full scale lets one outlier weight set the lattice; pulling full scale in to
    ``c * max|w|`` trades a little clipping for a finer lattice where the weights are.

    Each candidate is quantised by the array's own quantiser, so the search sees exactly
    what ``program()`` will do, round-half-away-from-zero included. It takes train data
    only: choosing on the test set would make the reported accuracy a fit to it. Ties go
    to the larger ``c``, the one that clips least.
    """
    cb = Crossbar(weights.shape[0], weights.shape[1], scheme=scheme, states=states)
    best_c, best_acc = None, -1.0
    for c in SCALE_CANDIDATES:  # ascending, so ">=" hands a tie to the larger c
        q = cb.quantise_weights(scale_to_window(weights, c))
        acc = accuracy(x_train @ q, train_labels)
        if acc >= best_acc:
            best_c, best_acc = c, acc
    return best_c


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
    p.add_argument("--lr", type=float, default=None,
                   help="default 0.5 * 36 / rows, so exactly 0.5 at the row's 36 inputs")
    p.add_argument("--grid", type=int, default=ROW_GRID,
                   help="image grid g; rows = g*g. 6 is the shared task")
    p.add_argument("--out-dir", default=None,
                   help="default exports/ at grid 6, else exports/size/g<gg>/")
    p.add_argument("--batch", type=int, default=128)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--scheme", default="differential", choices=("differential", "offset"))
    p.add_argument("--ratio", type=float, default=None,
                   help="g_max / g_min for a sensitivity handoff, g_min held at 1 uS; "
                        "the row's grid only. Default: the design's window")
    p.add_argument("--calibrate-states", type=int, default=None, metavar="S",
                   help="write the row's weights with full scale at c*max|w|, c chosen on "
                        "the train set at S levels per device, into exports/scale/s<S>/; "
                        "the row's grid only")
    p.add_argument("--quick", action="store_true", help="fast smoke config")
    return p.parse_args()


def main():
    args = parse_args()
    if args.quick:
        args.epochs = 5

    if args.ratio is not None and args.grid != ROW_GRID:
        raise SystemExit("--ratio is a sensitivity of the row's own array; use it at grid 6")
    if args.calibrate_states is not None:
        if args.grid != ROW_GRID:
            raise SystemExit("--calibrate-states is a sensitivity of the row's own array; "
                             "use it at grid 6")
        if args.ratio is not None:
            raise SystemExit("--calibrate-states and --ratio are separate sensitivities of "
                             "the row; run one at a time")
        if args.calibrate_states < 2:
            raise SystemExit("--calibrate-states needs at least 2 levels per device")

    task = load_shared_task(args.grid)
    cb = ratio_crossbar(task.n_channels, N_CLASSES, args.ratio, scheme=args.scheme)
    if args.lr is None:
        args.lr = learning_rate(cb.n_inputs)
    if args.out_dir:
        out_dir = args.out_dir
    elif args.ratio is not None:
        out_dir = ratio_dir(args.ratio)
    elif args.calibrate_states is not None:
        out_dir = scale_dir(args.calibrate_states)
    else:
        out_dir = output_dir(args.grid)

    # The array's own encoding, used for training as well as evaluation, so there
    # is one preprocessing path rather than two that can drift.
    x_train = cb.encode(task.train_images) / cb.read_voltage
    x_test = cb.encode(task.test_images) / cb.read_voltage
    y_train = one_hot(task.train_labels, N_CLASSES)

    print(f"crossbar   {cb.n_inputs}x{cb.n_outputs}, {args.scheme}, "
          f"{cb.n_devices} devices, window ratio {cb.ratio:g}")
    print(f"task       train {task.train_images.shape}, test {task.test_images.shape}")
    print(f"training   lr {args.lr:g}, {args.epochs} epochs, seed {args.seed}")

    raw, losses = None, []
    for epoch, loss, raw in train(
        x_train, y_train, epochs=args.epochs, lr=args.lr, batch=args.batch,
        seed=args.seed,
    ):
        losses.append(loss)
        if epoch % 10 == 0 or epoch == args.epochs - 1:
            acc = accuracy(x_test @ raw, task.test_labels)
            print(f"  epoch {epoch:3d}  loss {loss:.4f}  test acc {acc:.4f}")

    # The gate on the learning-rate rule: a loss still moving, or moving up, at the
    # end says the descent did not settle and the accuracy below is the optimiser's.
    tail = losses[-10:]
    print(f"loss over the last {len(tail)} epochs: {tail[0]:.4f} -> {tail[-1]:.4f} "
          f"(change {tail[-1] - tail[0]:+.4f}, worst step {max(np.diff(tail)):+.5f})")

    weights, gain = fit_to_window(raw)
    assert accuracy(x_test @ weights, task.test_labels) == accuracy(
        x_test @ raw, task.test_labels
    ), "rescaling into the window changed a prediction; it must not"

    # The calibrated variant moves full scale in from max|w| to c*max|w|. Unlike the
    # rescaling above this one *can* change a prediction -- it clips -- so the ideal
    # recorded below is the continuous accuracy of the clipped weights, not the row's.
    c = None
    if args.calibrate_states is not None:
        row_weights = weights
        c = calibrate_scale(row_weights, x_train, task.train_labels,
                            args.calibrate_states, scheme=args.scheme)
        weights = scale_to_window(row_weights, c)
        gain = gain * c
        print(f"\ncalibrated scale  c = {c:.2f} of max|w|, chosen on the train set at "
              f"{args.calibrate_states} states per device")

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
    if c is not None:
        qcb = Crossbar(cb.n_inputs, cb.n_outputs, scheme=args.scheme,
                       states=args.calibrate_states)
        q_cal = accuracy(qcb.forward(task.test_images, weights), task.test_labels)
        q_row = accuracy(qcb.forward(task.test_images, row_weights), task.test_labels)
        print(f"at {args.calibrate_states} states   {q_cal:.4f} calibrated "
              f"(c = {c:.2f}), {q_row:.4f} at the row's own max|w| scale")

    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "crossbar_ideal.npz")
    np.savez_compressed(
        out, weights=weights, readout_gain=gain, seed=args.seed, scheme=args.scheme,
        ideal_accuracy=ideal, epochs=args.epochs, lr=args.lr, batch=args.batch,
        grid=args.grid,
        **({} if c is None else {"scale_c": c, "calibrated_states": args.calibrate_states}),
    )
    print(f"wrote {out}")

    handoff = os.path.join(out_dir, "crossbar_handoff.h5")
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
