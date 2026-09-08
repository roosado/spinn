"""The ideal crossbar: a matrix-vector multiply performed by the wiring.

Devices sit at the intersections of a grid. Each row is driven with a voltage, each
device passes a current set by its own conductance, and every device on a column
dumps its current into the same wire. The wire adds them, because that is what a
wire does. One settling time, no instructions, and the arithmetic is Ohm's law and
Kirchhoff's current law rather than an algorithm.

Everything here is **ideal**: exact conductances, no variation, no wire resistance,
no read noise. Those live behind the handoff, in MATLAB, and the boundary is
one-directional on purpose -- a design that can be quietly adjusted to flatter its
own error budget is not a measurement of anything.

Three things this module has to be explicit about, because each changes the error
budget downstream and none of them is recoverable from the code by inspection:

**Signed weights.** A conductance cannot be negative, so a signed weight needs a
scheme. Both are implemented and the choice is a parameter, because it has to
cross the handoff rather than be assumed independently on each side. The default
is ``"differential"``; the argument is in :class:`Crossbar`.

**Where quantisation applies.** To the *devices*, not to the weight. A device holds
a state; that is the physical object with a finite number of levels. Under a
differential pair the effective weight is a difference of two quantised
conductances, which resolves more finely than either device does -- modelling it
on the weight instead would understate the scheme and make error source 2 look
worse than it is.

**Which numbers matter.** ``g_min``, ``g_max`` and ``read_voltage`` are all
``UNSOURCED``. The ideal accuracy does not depend on them: they scale out of the
decode, exactly. They are carried because the error model needs them, and because
a conductance window with no numbers in it invites someone to invent some.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Placeholder conductance window, in siemens.
#:
#: UNSOURCED -- both endpoints. MTJ and domain-wall parameters are spread across a
#: literature that mixes measurements with roadmap projections, and no distribution
#: has been read into this repo yet.
#:
#: The *ratio* is the number that matters and it is the platform's characteristic
#: constraint -- the counterpart of photonn's 2*pi phase range, and far smaller.
#: Every distinguishable weight state and every noise margin has to fit inside it.
#: See ``docs/history.md``. Nothing in this module depends on either value.
G_MIN = 1.0e-6  # UNSOURCED
G_MAX = 3.0e-6  # UNSOURCED

#: Read voltage, volts. UNSOURCED. Sets the input scale and hence the current, so
#: it matters to energy and to shot noise, and not at all to the ideal accuracy.
READ_VOLTAGE = 0.1  # UNSOURCED

SCHEMES = ("differential", "offset")


@dataclass(frozen=True)
class Crossbar:
    """An ideal crossbar, and the scheme by which it represents a signed weight.

    Parameters
    ----------
    n_inputs, n_outputs
        Rows and columns of the logical weight matrix.
    scheme
        ``"differential"`` -- two devices per weight, wired so their currents
        subtract. ``"offset"`` -- one device per weight, with zero at mid-scale and
        a pedestal subtracted downstream.
    states
        Distinguishable levels **per device**, or ``None`` for the ideal case.
        Binary MTJ is 2; a domain-wall device resolves more. One knob, two
        families. This is error source 2 and is off for the ideal baseline.
    g_min, g_max, read_voltage
        The physical window and drive. All ``UNSOURCED``; none affects accuracy.

    Why differential is the default
    -------------------------------
    It costs twice the devices, and it is still the better trade here:

    ===========================  ====================  ====================
    ..                           differential          offset
    ===========================  ====================  ====================
    devices per weight           two                   one
    signed range from the window ``+/-(g_max-g_min)``  ``+/-(g_max-g_min)/2``
    a zero weight is             two equal states      one mid-scale state
    conductance-variation draws  two, independent      one
    the column pedestal          cancels in hardware   subtracted downstream
    ===========================  ====================  ====================

    The window is this platform's binding physical constraint, so **doubling the
    signed range you get out of it is worth real devices**. Two independent draws
    per weight raise the effective weight's sigma by sqrt(2), against a range that
    doubles -- a net gain of sqrt(2) in signal-to-noise, before counting the
    pedestal.

    The pedestal is the second half. Under ``"offset"`` every column carries a
    large baseline current that depends on the input, and subtracting its *mean*
    downstream does not subtract the *noise* on it. A differential pair rejects it
    in the wiring, where it costs nothing.

    Recorded as a decision rather than a default: it is revisitable, it crosses the
    handoff explicitly, and error source 1 lands differently under each.
    """

    n_inputs: int
    n_outputs: int
    scheme: str = "differential"
    states: int | None = None
    g_min: float = G_MIN
    g_max: float = G_MAX
    read_voltage: float = READ_VOLTAGE

    def __post_init__(self) -> None:
        if self.scheme not in SCHEMES:
            raise ValueError(f"scheme must be one of {SCHEMES}; got {self.scheme!r}")
        if not self.g_max > self.g_min > 0:
            raise ValueError(f"need 0 < g_min < g_max; got {self.g_min}, {self.g_max}")
        if self.states is not None and self.states < 2:
            raise ValueError(f"states must be at least 2; got {self.states}")

    @property
    def span(self) -> float:
        """``g_max - g_min``: the usable conductance swing of one device."""
        return self.g_max - self.g_min

    @property
    def ratio(self) -> float:
        """``g_max / g_min``. The platform's characteristic constraint."""
        return self.g_max / self.g_min

    @property
    def devices_per_weight(self) -> int:
        return 2 if self.scheme == "differential" else 1

    @property
    def n_devices(self) -> int:
        return self.n_inputs * self.n_outputs * self.devices_per_weight

    # -- programming ---------------------------------------------------------

    def quantise(self, g: np.ndarray) -> np.ndarray:
        """Snap conductances to ``states`` levels across ``[g_min, g_max]``.

        A bounded range, not a cyclic one. photonn's quantiser wraps to ``[0, 2*pi)``
        because a phase is cyclic; applying that here would wrap the largest weight
        onto the smallest, which is not subtle but would still produce a plausible
        accuracy.
        """
        if self.states is None:
            return g
        levels = self.states - 1
        step = self.span / levels
        return self.g_min + np.round((g - self.g_min) / step) * step

    def program(self, weights: np.ndarray) -> np.ndarray:
        """Map weights in ``[-1, 1]`` onto device conductances.

        Returns ``(2, n_inputs, n_outputs)`` for a differential pair -- the positive
        and negative rails -- and ``(1, n_inputs, n_outputs)`` for an offset. The
        leading axis is the device index within one weight, so both schemes present
        the same shape to everything downstream, including the handoff.
        """
        w = np.clip(np.asarray(weights, dtype="f8"), -1.0, 1.0)
        if w.shape != (self.n_inputs, self.n_outputs):
            raise ValueError(
                f"weights must be {(self.n_inputs, self.n_outputs)}; got {w.shape}"
            )
        if self.scheme == "differential":
            g_pos = self.g_min + (1.0 + w) / 2.0 * self.span
            g_neg = self.g_min + (1.0 - w) / 2.0 * self.span
            g = np.stack([g_pos, g_neg])
        else:
            g = (self.g_min + (1.0 + w) / 2.0 * self.span)[None]
        return self.quantise(g)

    # -- reading -------------------------------------------------------------

    def encode(self, images: np.ndarray) -> np.ndarray:
        """Flatten images to row voltages, scaled to the read voltage.

        Per-sample L-infinity normalisation: the physical constraint is a maximum
        read voltage, so the largest pixel in each sample sits at ``read_voltage``.

        The frozen task ships unit-L2 because photonn's constraint is optical power
        instead. Both are per-sample positive scalings of the same non-negative
        vector, so dividing by the maximum here recovers exactly what L-infinity
        normalisation of the raw grid would have given. A scale is recoverable; an
        offset would not have been.
        """
        v = np.asarray(images, dtype="f8").reshape(len(images), -1)
        if v.shape[1] != self.n_inputs:
            raise ValueError(f"expected {self.n_inputs} inputs; got {v.shape[1]}")
        peak = np.max(np.abs(v), axis=1, keepdims=True)
        return self.read_voltage * v / np.where(peak > 0, peak, 1.0)


    def currents(self, voltages: np.ndarray, conductances: np.ndarray) -> np.ndarray:
        """Column currents: ``I = V @ G`` per device rail. Kirchhoff, and nothing else."""
        return np.einsum("bi,dio->dbo", voltages, conductances)

    def decode(self, currents: np.ndarray, voltages: np.ndarray) -> np.ndarray:
        """Column currents back to logits, undoing the scheme's representation.

        Both schemes divide out ``read_voltage * span``, which is why neither the
        conductance window nor the drive affects the ideal accuracy: they cancel
        here exactly.
        """
        scale = self.read_voltage * self.span
        if self.scheme == "differential":
            return (currents[0] - currents[1]) / scale
        # One rail, so the column carries a baseline set by the inputs rather than
        # by the weights. It is exactly computable and exactly subtracted here --
        # in hardware it is a real current that a differential pair never draws.
        drive = voltages.sum(axis=1, keepdims=True)
        pedestal = drive * (self.g_min + self.span / 2.0)
        return (currents[0] - pedestal) / (scale / 2.0)

    def forward(self, images: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """Logits for a batch of images. The whole ideal forward pass."""
        v = self.encode(images)
        return self.decode(self.currents(v, self.program(weights)), v)


def predict(logits: np.ndarray) -> np.ndarray:
    return np.argmax(logits, axis=1)


def accuracy(logits: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean(predict(logits) == np.asarray(labels)))
